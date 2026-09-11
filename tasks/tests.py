"""
Comprehensive test suite for the TaskManager application.

Tests cover:
- Authentication (register, login, logout, unauthenticated access)
- Project CRUD and owner-only permissions
- Task CRUD and owner-only permissions
- Project membership / view access (IDOR prevention)
- Comment creation (member access only, append-only)
- Overdue task query correctness
- Per-project status counts (annotate + Count)
- Dashboard content
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Comment, Priority, Project, Status, Task

User = get_user_model()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_user(username, password="testpass123"):
    return User.objects.create_user(username=username, password=password)


def make_project(owner, name="Test Project"):
    return Project.objects.create(name=name, description="desc", owner=owner)


def make_task(project, assigned_to=None, status=Status.TODO,
              priority=Priority.MEDIUM, due_date=None, title="Test Task"):
    return Task.objects.create(
        title=title,
        project=project,
        assigned_to=assigned_to,
        status=status,
        priority=priority,
        due_date=due_date,
    )


# ─── Auth Tests ───────────────────────────────────────────────────────────────

class AuthTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_register_creates_user_and_logs_in(self):
        resp = self.client.post(reverse("accounts:register"), {
            "username": "newuser",
            "email": "newuser@test.com",
            "password1": "StrongPass99!",
            "password2": "StrongPass99!",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        # After registration the user should be logged in (dashboard accessible)
        resp2 = self.client.get(reverse("tasks:dashboard"))
        self.assertEqual(resp2.status_code, 200)

    def test_login_works(self):
        make_user("loginuser")
        resp = self.client.post(reverse("accounts:login"), {
            "username": "loginuser",
            "password": "testpass123",
        })
        self.assertEqual(resp.status_code, 302)

    def test_unauthenticated_dashboard_redirects_to_login(self):
        resp = self.client.get(reverse("tasks:dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    def test_unauthenticated_project_list_redirects(self):
        resp = self.client.get(reverse("tasks:project_list"))
        self.assertEqual(resp.status_code, 302)

    def test_unauthenticated_project_create_redirects(self):
        resp = self.client.get(reverse("tasks:project_create"))
        self.assertEqual(resp.status_code, 302)

    def test_logout_works(self):
        user = make_user("logoutuser")
        self.client.force_login(user)
        resp = self.client.post(reverse("accounts:logout"))
        self.assertEqual(resp.status_code, 302)
        # After logout, dashboard should redirect to login
        resp2 = self.client.get(reverse("tasks:dashboard"))
        self.assertEqual(resp2.status_code, 302)


# ─── Project Permission Tests ─────────────────────────────────────────────────

class ProjectPermissionTests(TestCase):

    def setUp(self):
        self.owner = make_user("owner")
        self.other = make_user("other")
        self.project = make_project(self.owner)
        self.client = Client()

    def test_owner_can_get_edit_page(self):
        self.client.force_login(self.owner)
        resp = self.client.get(reverse("tasks:project_edit", kwargs={"pk": self.project.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_owner_can_post_edit(self):
        self.client.force_login(self.owner)
        resp = self.client.post(
            reverse("tasks:project_edit", kwargs={"pk": self.project.pk}),
            {"name": "Updated Name", "description": "new desc"},
        )
        self.assertEqual(resp.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Updated Name")

    def test_owner_can_delete(self):
        self.client.force_login(self.owner)
        pk = self.project.pk
        resp = self.client.post(reverse("tasks:project_delete", kwargs={"pk": pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Project.objects.filter(pk=pk).exists())

    def test_non_owner_edit_get_returns_403(self):
        self.client.force_login(self.other)
        resp = self.client.get(reverse("tasks:project_edit", kwargs={"pk": self.project.pk}))
        self.assertEqual(resp.status_code, 403)

    def test_non_owner_edit_post_returns_403(self):
        """Direct POST from non-owner must fail with 403 regardless of UI."""
        self.client.force_login(self.other)
        resp = self.client.post(
            reverse("tasks:project_edit", kwargs={"pk": self.project.pk}),
            {"name": "Hacked Name", "description": "hacked"},
        )
        self.assertEqual(resp.status_code, 403)
        self.project.refresh_from_db()
        self.assertNotEqual(self.project.name, "Hacked Name")

    def test_non_owner_delete_post_returns_403(self):
        """Direct POST from non-owner must fail with 403."""
        self.client.force_login(self.other)
        resp = self.client.post(reverse("tasks:project_delete", kwargs={"pk": self.project.pk}))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_create_project_sets_owner_to_requesting_user(self):
        self.client.force_login(self.other)
        resp = self.client.post(reverse("tasks:project_create"), {
            "name": "New Project",
            "description": "test",
        })
        self.assertEqual(resp.status_code, 302)
        proj = Project.objects.get(name="New Project")
        self.assertEqual(proj.owner, self.other)


# ─── Project Membership / IDOR Tests ─────────────────────────────────────────

class ProjectMembershipTests(TestCase):

    def setUp(self):
        self.owner = make_user("owner")
        self.assigned = make_user("assigned")
        self.stranger = make_user("stranger")
        self.project = make_project(self.owner)
        self.task = make_task(self.project, assigned_to=self.assigned)
        self.client = Client()

    def test_owner_can_view_project(self):
        self.client.force_login(self.owner)
        resp = self.client.get(reverse("tasks:project_detail", kwargs={"pk": self.project.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_assigned_member_can_view_project(self):
        self.client.force_login(self.assigned)
        resp = self.client.get(reverse("tasks:project_detail", kwargs={"pk": self.project.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_stranger_cannot_view_project(self):
        """Non-member guessing a project ID must get 403, not 200."""
        self.client.force_login(self.stranger)
        resp = self.client.get(reverse("tasks:project_detail", kwargs={"pk": self.project.pk}))
        self.assertEqual(resp.status_code, 403)

    def test_stranger_cannot_view_task(self):
        """Non-member guessing a task ID must get 403."""
        self.client.force_login(self.stranger)
        resp = self.client.get(reverse("tasks:task_detail", kwargs={"pk": self.task.pk}))
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_view_project(self):
        resp = self.client.get(reverse("tasks:project_detail", kwargs={"pk": self.project.pk}))
        self.assertEqual(resp.status_code, 302)


# ─── Task Permission Tests ────────────────────────────────────────────────────

class TaskPermissionTests(TestCase):

    def setUp(self):
        self.owner = make_user("owner")
        self.assigned = make_user("assigned")
        self.stranger = make_user("stranger")
        self.project = make_project(self.owner)
        self.task = make_task(self.project, assigned_to=self.assigned)
        self.client = Client()

    def test_owner_can_create_task(self):
        self.client.force_login(self.owner)
        resp = self.client.post(
            reverse("tasks:task_create", kwargs={"project_pk": self.project.pk}),
            {"title": "New Task", "status": "TODO", "priority": "MEDIUM"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Task.objects.filter(title="New Task").exists())

    def test_non_owner_cannot_create_task(self):
        """Assigned user cannot create tasks — only the project owner can."""
        self.client.force_login(self.assigned)
        resp = self.client.post(
            reverse("tasks:task_create", kwargs={"project_pk": self.project.pk}),
            {"title": "Hacked Task", "status": "TODO", "priority": "MEDIUM"},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Task.objects.filter(title="Hacked Task").exists())

    def test_owner_can_edit_task(self):
        self.client.force_login(self.owner)
        resp = self.client.post(
            reverse("tasks:task_edit", kwargs={"pk": self.task.pk}),
            {"title": "Updated Task", "status": "IN_PROGRESS", "priority": "HIGH"},
        )
        self.assertEqual(resp.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Updated Task")

    def test_assigned_user_cannot_edit_task(self):
        """Being assigned does NOT grant edit rights — only owner can edit."""
        self.client.force_login(self.assigned)
        resp = self.client.post(
            reverse("tasks:task_edit", kwargs={"pk": self.task.pk}),
            {"title": "Hijacked", "status": "DONE", "priority": "LOW"},
        )
        self.assertEqual(resp.status_code, 403)
        self.task.refresh_from_db()
        self.assertNotEqual(self.task.title, "Hijacked")

    def test_stranger_cannot_edit_task(self):
        self.client.force_login(self.stranger)
        resp = self.client.post(
            reverse("tasks:task_edit", kwargs={"pk": self.task.pk}),
            {"title": "Hijacked", "status": "DONE", "priority": "LOW"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_owner_can_delete_task(self):
        self.client.force_login(self.owner)
        pk = self.task.pk
        resp = self.client.post(reverse("tasks:task_delete", kwargs={"pk": pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Task.objects.filter(pk=pk).exists())

    def test_assigned_user_cannot_delete_task(self):
        self.client.force_login(self.assigned)
        resp = self.client.post(reverse("tasks:task_delete", kwargs={"pk": self.task.pk}))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_stranger_cannot_delete_task(self):
        self.client.force_login(self.stranger)
        resp = self.client.post(reverse("tasks:task_delete", kwargs={"pk": self.task.pk}))
        self.assertEqual(resp.status_code, 403)


# ─── Comment Tests ────────────────────────────────────────────────────────────

class CommentTests(TestCase):

    def setUp(self):
        self.owner = make_user("owner")
        self.member = make_user("member")
        self.stranger = make_user("stranger")
        self.project = make_project(self.owner)
        self.task = make_task(self.project, assigned_to=self.member)
        self.client = Client()

    def test_owner_can_comment(self):
        self.client.force_login(self.owner)
        resp = self.client.post(
            reverse("tasks:task_detail", kwargs={"pk": self.task.pk}),
            {"body": "Owner comment"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Comment.objects.filter(body="Owner comment", author=self.owner).exists())

    def test_member_can_comment(self):
        self.client.force_login(self.member)
        resp = self.client.post(
            reverse("tasks:task_detail", kwargs={"pk": self.task.pk}),
            {"body": "Member comment"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Comment.objects.filter(body="Member comment", author=self.member).exists())

    def test_stranger_cannot_comment(self):
        """Non-member POST to task detail must return 403."""
        self.client.force_login(self.stranger)
        resp = self.client.post(
            reverse("tasks:task_detail", kwargs={"pk": self.task.pk}),
            {"body": "Unauthorized comment"},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Comment.objects.filter(body="Unauthorized comment").exists())

    def test_unauthenticated_cannot_comment(self):
        resp = self.client.post(
            reverse("tasks:task_detail", kwargs={"pk": self.task.pk}),
            {"body": "Anon comment"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Comment.objects.filter(body="Anon comment").exists())


# ─── Overdue Query Tests ──────────────────────────────────────────────────────

class OverdueQueryTests(TestCase):
    """Verify Task.objects.overdue() is correct in all edge cases."""

    def setUp(self):
        self.owner = make_user("owner")
        self.project = make_project(self.owner)
        self.today = date.today()

    def test_past_todo_is_overdue(self):
        t = make_task(self.project, status=Status.TODO, due_date=self.today - timedelta(days=1))
        self.assertIn(t, Task.objects.overdue())

    def test_past_in_progress_is_overdue(self):
        t = make_task(self.project, status=Status.IN_PROGRESS, due_date=self.today - timedelta(days=1))
        self.assertIn(t, Task.objects.overdue())

    def test_past_done_is_not_overdue(self):
        t = make_task(self.project, status=Status.DONE, due_date=self.today - timedelta(days=1))
        self.assertNotIn(t, Task.objects.overdue())

    def test_future_unfinished_is_not_overdue(self):
        t = make_task(self.project, status=Status.TODO, due_date=self.today + timedelta(days=1))
        self.assertNotIn(t, Task.objects.overdue())

    def test_no_due_date_is_not_overdue(self):
        """Nullable due_date means the task is not overdue."""
        t = make_task(self.project, status=Status.TODO, due_date=None)
        self.assertNotIn(t, Task.objects.overdue())

    def test_due_today_is_not_overdue(self):
        """due_date == today is NOT overdue (condition is strictly <)."""
        t = make_task(self.project, status=Status.TODO, due_date=self.today)
        self.assertNotIn(t, Task.objects.overdue())

    def test_overdue_only_includes_correct_tasks(self):
        overdue = make_task(self.project, status=Status.TODO, due_date=self.today - timedelta(days=3), title="Overdue")
        done_past = make_task(self.project, status=Status.DONE, due_date=self.today - timedelta(days=3), title="DonePast")
        future = make_task(self.project, status=Status.TODO, due_date=self.today + timedelta(days=3), title="Future")
        no_date = make_task(self.project, status=Status.TODO, due_date=None, title="NoDate")
        qs = Task.objects.overdue()
        self.assertIn(overdue, qs)
        self.assertNotIn(done_past, qs)
        self.assertNotIn(future, qs)
        self.assertNotIn(no_date, qs)

    def test_overdue_is_composable(self):
        """overdue() must be a queryset method that can be chained."""
        make_task(self.project, status=Status.TODO, due_date=self.today - timedelta(days=1), title="OD1")
        # Chain with filter
        qs = Task.objects.overdue().filter(project=self.project)
        self.assertEqual(qs.count(), 1)


# ─── Status Counts Tests ──────────────────────────────────────────────────────

class StatusCountTests(TestCase):

    def setUp(self):
        self.owner = make_user("owner")
        self.project = make_project(self.owner)
        self.client = Client()
        self.client.force_login(self.owner)

    @staticmethod
    def _get_counts(project):
        from django.db.models import Count
        rows = (
            Task.objects
            .filter(project=project)
            .values("status")
            .annotate(count=Count("id"))
        )
        return {row["status"]: row["count"] for row in rows}

    def test_empty_project_has_no_counts(self):
        counts = self._get_counts(self.project)
        self.assertEqual(counts.get(Status.TODO, 0), 0)

    def test_counts_match_actual_tasks(self):
        make_task(self.project, status=Status.TODO, title="t1")
        make_task(self.project, status=Status.TODO, title="t2")
        make_task(self.project, status=Status.IN_PROGRESS, title="t3")
        make_task(self.project, status=Status.DONE, title="t4")
        counts = self._get_counts(self.project)
        self.assertEqual(counts[Status.TODO], 2)
        self.assertEqual(counts[Status.IN_PROGRESS], 1)
        self.assertEqual(counts[Status.DONE], 1)

    def test_project_detail_context_has_counts(self):
        """counts_by_status must be in the template context."""
        make_task(self.project, status=Status.TODO, title="t1")
        make_task(self.project, status=Status.DONE, title="t2")
        resp = self.client.get(reverse("tasks:project_detail", kwargs={"pk": self.project.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("counts_by_status", resp.context)
        counts = resp.context["counts_by_status"]
        self.assertEqual(counts.get(Status.TODO, 0), 1)
        self.assertEqual(counts.get(Status.DONE, 0), 1)

    def test_counts_are_isolated_per_project(self):
        """Counts for one project must not bleed into another."""
        other_project = make_project(self.owner, name="Other")
        make_task(self.project, status=Status.TODO, title="p1t1")
        make_task(other_project, status=Status.TODO, title="p2t1")
        make_task(other_project, status=Status.TODO, title="p2t2")
        counts_p1 = self._get_counts(self.project)
        counts_p2 = self._get_counts(other_project)
        self.assertEqual(counts_p1[Status.TODO], 1)
        self.assertEqual(counts_p2[Status.TODO], 2)


# ─── Dashboard Tests ──────────────────────────────────────────────────────────

class DashboardTests(TestCase):

    def setUp(self):
        self.user = make_user("dashuser")
        self.other = make_user("other")
        self.project = make_project(self.user)
        self.client = Client()
        self.client.force_login(self.user)

    def test_dashboard_shows_assigned_todo_tasks(self):
        t = make_task(self.project, assigned_to=self.user, status=Status.TODO, title="My Task")
        resp = self.client.get(reverse("tasks:dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(t, resp.context["todo_tasks"])

    def test_dashboard_does_not_show_others_tasks(self):
        t = make_task(self.project, assigned_to=self.other, status=Status.TODO, title="Other Task")
        resp = self.client.get(reverse("tasks:dashboard"))
        self.assertNotIn(t, resp.context["todo_tasks"])

    def test_dashboard_shows_overdue_tasks(self):
        make_task(
            self.project, assigned_to=self.user,
            status=Status.TODO,
            due_date=date.today() - timedelta(days=1),
            title="Overdue Task",
        )
        resp = self.client.get(reverse("tasks:dashboard"))
        self.assertGreater(len(resp.context["overdue_tasks"]), 0)

    def test_dashboard_groups_by_status(self):
        todo = make_task(self.project, assigned_to=self.user, status=Status.TODO, title="Todo")
        ip = make_task(self.project, assigned_to=self.user, status=Status.IN_PROGRESS, title="IP")
        done = make_task(self.project, assigned_to=self.user, status=Status.DONE, title="Done")
        resp = self.client.get(reverse("tasks:dashboard"))
        self.assertIn(todo, resp.context["todo_tasks"])
        self.assertIn(ip, resp.context["in_progress_tasks"])
        self.assertIn(done, resp.context["done_tasks"])
