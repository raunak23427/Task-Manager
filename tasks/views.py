"""
Task manager views.

Permission model
----------------
- All views require @login_required.
- Mutating views (edit/delete) for a Project raise PermissionDenied (HTTP 403)
  if request.user is not the project owner.
- The same rule applies to Task CRUD: only the *project owner* can create,
  edit, or delete tasks within their project.
- Being *assigned* to a task does NOT grant edit/delete rights.
- Read views (project detail, task detail) are accessible to any "member"
  (owner OR any user assigned to at least one task in the project).
- Comment creation is open to any authenticated member who can view the task.

Ownership checks are enforced at the view/server layer — NOT only by hiding
buttons in templates.  A direct POST from a non-owner always returns 403.

N+1 avoidance
-------------
- Task lists use select_related('assigned_to') — one JOIN, not N queries.
- Dashboard uses select_related('project') — avoids per-row project lookups.
- Task detail uses select_related('project', 'assigned_to', 'project__owner')
  and prefetch_related('comments__author') — fetches comments + authors in 2
  extra queries regardless of comment count.
- Project list uses select_related('owner') and prefetch_related('tasks').
"""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, ProjectForm, TaskForm
from .models import Comment, Priority, Project, Status, Task


# ─── Permission helpers ───────────────────────────────────────────────────────

def _require_owner(project, user):
    """
    Raise PermissionDenied if *user* is not the project owner.

    Used in every mutating view so that a direct HTTP POST from a non-owner
    always returns 403, regardless of what the template shows.
    """
    if project.owner != user:
        raise PermissionDenied


def _require_member(project, user):
    """Raise PermissionDenied if *user* is not a project member."""
    if not project.is_member(user):
        raise PermissionDenied


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """
    Landing page: current user's tasks grouped by status.

    select_related('project') on each queryset avoids N+1 when the template
    renders task.project.name for each task row.

    The 'overdue' section uses Task.objects.overdue() — the single reusable
    overdue-tasks query defined in managers.py.
    """
    base_qs = (
        Task.objects
        .filter(assigned_to=request.user)
        .select_related("project")
    )

    todo_tasks        = base_qs.filter(status=Status.TODO)
    in_progress_tasks = base_qs.filter(status=Status.IN_PROGRESS)
    done_tasks        = base_qs.filter(status=Status.DONE)

    # Overdue: reusable manager method — due_date < today, status != DONE
    overdue_tasks = (
        Task.objects
        .overdue()
        .filter(assigned_to=request.user)
        .select_related("project")
    )

    return render(request, "tasks/dashboard.html", {
        "todo_tasks":        todo_tasks,
        "in_progress_tasks": in_progress_tasks,
        "done_tasks":        done_tasks,
        "overdue_tasks":     overdue_tasks,
    })


# ─── Projects ─────────────────────────────────────────────────────────────────

@login_required
def project_list(request):
    """
    List all projects visible to the current user (owned or assigned-member).

    Uses a single Q-filter to avoid the Django 4.2 restriction on combining
    unique and non-unique querysets with |.
    select_related('owner') and prefetch_related('tasks') prevent N+1.
    """
    projects = (
        Project.objects
        .filter(Q(owner=request.user) | Q(tasks__assigned_to=request.user))
        .distinct()
        .select_related("owner")
        .prefetch_related("tasks")
    )
    return render(request, "tasks/project_list.html", {"projects": projects})


@login_required
def project_create(request):
    """Create a new project owned by the requesting user."""
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
    Project detail: per-project status counts + task table + overdue tasks.

    Status counts use annotate(count=Count('id')).values('status') — one
    GROUP BY query, no Python-level counting.

    Task list uses select_related('assigned_to') to avoid N+1 per row.
    """
    project = get_object_or_404(Project.objects.select_related("owner"), pk=pk)
    _require_member(project, request.user)

    # ── Per-project status counts (annotate + Count — one SQL query) ───────────
    status_counts = (
        Task.objects
        .filter(project=project)
        .values("status")
        .annotate(count=Count("id"))
    )
    counts_by_status = {row["status"]: row["count"] for row in status_counts}

    # ── Task list with N+1 avoidance ──────────────────────────────────────────
    tasks = (
        Task.objects
        .filter(project=project)
        .select_related("assigned_to")
        .order_by("status", "due_date")
    )

    overdue_tasks = (
        Task.objects
        .overdue()
        .filter(project=project)
        .select_related("assigned_to")
    )

    return render(request, "tasks/project_detail.html", {
        "project":          project,
        "tasks":            tasks,
        "overdue_tasks":    overdue_tasks,
        "counts_by_status": counts_by_status,
        "Status":           Status,
        "Priority":         Priority,
        "is_owner":         project.owner == request.user,
    })


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    _require_owner(project, request.user)  # ← HTTP 403 for non-owners

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect("tasks:project_detail", pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, "tasks/project_form.html", {
        "form": form, "action": "Edit", "project": project,
    })


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    _require_owner(project, request.user)  # ← HTTP 403 for non-owners

    if request.method == "POST":
        project.delete()
        return redirect("tasks:project_list")
    return render(request, "tasks/project_confirm_delete.html", {"project": project})


# ─── Tasks ────────────────────────────────────────────────────────────────────

@login_required
def task_create(request, project_pk):
    """Only the project owner can create tasks."""
    project = get_object_or_404(Project, pk=project_pk)
    _require_owner(project, request.user)  # ← HTTP 403 for non-owners

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.save()
            return redirect("tasks:task_detail", pk=task.pk)
    else:
        form = TaskForm()
    return render(request, "tasks/task_form.html", {
        "form": form, "project": project, "action": "Create",
    })


@login_required
def task_detail(request, pk):
    """
    Task detail with append-only comments.

    select_related('project', 'assigned_to', 'project__owner') joins three
    tables in one query.
    prefetch_related('comments__author') fetches all comments and their
    authors in exactly 2 additional queries regardless of comment count.
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

    return render(request, "tasks/task_detail.html", {
        "task":         task,
        "comment_form": comment_form,
        "is_owner":     task.project.owner == request.user,
        "Status":       Status,
        "Priority":     Priority,
    })


@login_required
def task_edit(request, pk):
    """Only the project owner can edit tasks."""
    task = get_object_or_404(Task.objects.select_related("project"), pk=pk)
    _require_owner(task.project, request.user)  # ← HTTP 403 for non-owners

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect("tasks:task_detail", pk=task.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, "tasks/task_form.html", {
        "form": form, "project": task.project, "action": "Edit", "task": task,
    })


@login_required
def task_delete(request, pk):
    """Only the project owner can delete tasks."""
    task = get_object_or_404(Task.objects.select_related("project"), pk=pk)
    _require_owner(task.project, request.user)  # ← HTTP 403 for non-owners

    if request.method == "POST":
        project_pk = task.project.pk
        task.delete()
        return redirect("tasks:project_detail", pk=project_pk)
    return render(request, "tasks/task_confirm_delete.html", {"task": task})
