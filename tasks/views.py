"""
Task manager views.

Permission model
----------------
- All views require authentication (@login_required).
- Mutating views (edit / delete) on a Project raise PermissionDenied (HTTP 403)
  if request.user is not the project owner.  The same applies to Task mutating
  views: the *project's* owner controls task creation, editing, and deletion.
- Read views (project detail, task detail) are accessible to any "member":
  the project owner OR a user assigned to at least one task in the project.
- Comment creation is open to any authenticated member who can view the task.

Ownership checks are enforced at the view layer — NOT just hidden in the
template.  A direct POST from a non-owner will receive a 403 response.

N+1 avoidance
-------------
- Task lists use select_related('assigned_to', 'project') so the assignee
  username and project name can be rendered without extra queries.
- Task detail uses prefetch_related('comments__author') so all comments and
  their authors are fetched in two queries, not one per comment.
- Dashboard querysets use select_related('project') to avoid per-row lookups.
"""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, ProjectForm, TaskForm
from .models import Comment, Priority, Project, Status, Task


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _require_owner(project, user):
    """
    Raise PermissionDenied if *user* is not the project owner.

    Called in every mutating view.  Ensures a direct HTTP request from a
    non-owner always returns 403, regardless of what the template shows.
    """
    if project.owner != user:
        raise PermissionDenied


def _require_member(project, user):
    """Raise PermissionDenied if *user* cannot read this project."""
    if not project.is_member(user):
        raise PermissionDenied


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """
    Landing page: current user's tasks grouped by status.

    Queryset selects related project in the same SQL query (select_related)
    to avoid N+1 when rendering the project name for each task row.

    Overdue tasks are fetched via the custom TaskQuerySet.overdue() method,
    which filters due_date < today and status != Done in one query.
    """
    base_qs = (
        Task.objects
        .filter(assigned_to=request.user)
        .select_related("project", "assigned_to")
    )

    todo_tasks        = base_qs.filter(status=Status.TODO)
    in_progress_tasks = base_qs.filter(status=Status.IN_PROGRESS)
    done_tasks        = base_qs.filter(status=Status.DONE)

    # Overdue: uses the reusable manager method (due_date < today, status != DONE)
    overdue_tasks = (
        Task.objects
        .overdue()
        .filter(assigned_to=request.user)
        .select_related("project")
    )

    context = {
        "todo_tasks":        todo_tasks,
        "in_progress_tasks": in_progress_tasks,
        "done_tasks":        done_tasks,
        "overdue_tasks":     overdue_tasks,
        "Status":            Status,
    }
    return render(request, "tasks/dashboard.html", context)


# ─── Projects ─────────────────────────────────────────────────────────────────

@login_required
def project_list(request):
    """
    List all projects visible to the current user:
    - Projects the user owns, OR
    - Projects where they are assigned to at least one task.

    prefetch_related('tasks') fetches all tasks for all returned projects
    in a single additional query (not one per project).
    """
    owned = Project.objects.filter(owner=request.user)
    member_of = Project.objects.filter(tasks__assigned_to=request.user).distinct()
    projects = (owned | member_of).distinct().prefetch_related("tasks").select_related("owner")
    return render(request, "tasks/project_list.html", {"projects": projects})


@login_required
def project_create(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            return redirect("tasks:project_detail", pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, "tasks/project_form.html", {"form": form, "action": "Create"})


@login_required
def project_detail(request, pk):
    """
    Project detail page with per-project status counts and task list.

    Status counts: annotate the Task queryset grouped by status using
    django.db.models.Count — one SQL query, no Python counting.

    Task list: select_related('assigned_to') avoids N+1 when rendering
    the assignee name for each task row.
    """
    project = get_object_or_404(Project, pk=pk)
    _require_member(project, request.user)

    # ── Per-project status counts (annotate + Count) ──────────────────────────
    # Produces:
    #   SELECT status, COUNT(id) AS count
    #   FROM tasks_task WHERE project_id = %s
    #   GROUP BY status
    status_counts = (
        Task.objects
        .filter(project=project)
        .values("status")
        .annotate(count=Count("id"))
    )
    # Build a dict for easy template access: {"TODO": 3, "IN_PROGRESS": 1, ...}
    counts_by_status = {row["status"]: row["count"] for row in status_counts}

    # ── Task list with N+1 avoidance ──────────────────────────────────────────
    tasks = (
        Task.objects
        .filter(project=project)
        .select_related("assigned_to")
        .order_by("status", "due_date")
    )

    # Overdue tasks within this project
    overdue_tasks = Task.objects.overdue().filter(project=project).select_related("assigned_to")

    context = {
        "project":         project,
        "tasks":           tasks,
        "overdue_tasks":   overdue_tasks,
        "counts_by_status": counts_by_status,
        "Status":          Status,
        "Priority":        Priority,
        "is_owner":        project.owner == request.user,
    }
    return render(request, "tasks/project_detail.html", context)


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    _require_owner(project, request.user)   # ← raises 403 for non-owners

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect("tasks:project_detail", pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, "tasks/project_form.html", {"form": form, "action": "Edit", "project": project})


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    _require_owner(project, request.user)   # ← raises 403 for non-owners

    if request.method == "POST":
        project.delete()
        return redirect("tasks:project_list")
    return render(request, "tasks/project_confirm_delete.html", {"project": project})


# ─── Tasks ────────────────────────────────────────────────────────────────────

@login_required
def task_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_owner(project, request.user)   # ← only project owner can add tasks

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.save()
            return redirect("tasks:task_detail", pk=task.pk)
    else:
        form = TaskForm()
    return render(request, "tasks/task_form.html", {"form": form, "project": project, "action": "Create"})


@login_required
def task_detail(request, pk):
    """
    Task detail with comments.

    prefetch_related('comments__author') fetches all comments and
    their authors in exactly two additional queries (not one per comment),
    regardless of how many comments exist.
    """
    task = get_object_or_404(
        Task.objects
        .select_related("project", "assigned_to", "project__owner")
        .prefetch_related("comments__author"),
        pk=pk,
    )
    _require_member(task.project, request.user)

    comment_form = CommentForm()

    if request.method == "POST":
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.task   = task
            comment.author = request.user
            comment.save()
            return redirect("tasks:task_detail", pk=task.pk)

    context = {
        "task":         task,
        "comment_form": comment_form,
        "is_owner":     task.project.owner == request.user,
        "Status":       Status,
        "Priority":     Priority,
    }
    return render(request, "tasks/task_detail.html", context)


@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task.objects.select_related("project"), pk=pk)
    _require_owner(task.project, request.user)  # ← raises 403 for non-owners

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect("tasks:task_detail", pk=task.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, "tasks/task_form.html", {"form": form, "project": task.project, "action": "Edit", "task": task})


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task.objects.select_related("project"), pk=pk)
    _require_owner(task.project, request.user)  # ← raises 403 for non-owners

    if request.method == "POST":
        project_pk = task.project.pk
        task.delete()
        return redirect("tasks:project_detail", pk=project_pk)
    return render(request, "tasks/task_confirm_delete.html", {"task": task})
