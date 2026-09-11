"""
Core data models: Project, Task, Comment.

Design notes
------------
- Status and Priority use Django's TextChoices (stored as VARCHAR, validated
  at the ORM layer, never free text).
- Task carries one deliberate composite index on (status, due_date) — see
  QUERIES.md for the full justification.
- Comment is append-only; no update/delete views or permissions are provided.
- "Membership" is implicit: owner OR any user who has been assigned_to at
  least one task in the project.  No extra M2M table is needed.
"""

from django.contrib.auth import get_user_model
from django.db import models

from .managers import TaskManager

User = get_user_model()


# ─── Choice enumerations ──────────────────────────────────────────────────────

class Status(models.TextChoices):
    TODO        = "TODO",        "To Do"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    DONE        = "DONE",        "Done"


class Priority(models.TextChoices):
    LOW    = "LOW",    "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH   = "HIGH",   "High"


# ─── Models ───────────────────────────────────────────────────────────────────

class Project(models.Model):
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner       = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_projects",
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def is_member(self, user):
        """
        Return True if *user* is the owner OR has been assigned to any task
        in this project.  Used by views to gate read access.
        """
        if self.owner_id == user.pk:
            return True
        return self.tasks.filter(assigned_to=user).exists()


class Task(models.Model):
    title       = models.CharField(max_length=300)
    status      = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
        db_index=False,   # covered by the composite index below
    )
    priority    = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    due_date    = models.DateField(null=True, blank=True)
    project     = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    assigned_to = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_tasks",
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    # Custom manager — exposes .overdue(), .for_user(), .for_project()
    objects = TaskManager()

    class Meta:
        ordering = ["due_date", "priority"]
        indexes = [
            # ── Deliberate composite index ────────────────────────────────────
            # Accelerates the overdue-tasks query:
            #   WHERE status != 'DONE' AND due_date < today
            # MySQL can skip the DONE bucket in the (status) prefix and then
            # apply the range predicate on due_date within each remaining
            # status value, avoiding a full table scan.
            # Also benefits the dashboard's per-status filtering.
            # See QUERIES.md §4 for EXPLAIN output.
            models.Index(fields=["status", "due_date"], name="idx_task_status_due_date"),
        ]

    def __str__(self):
        return self.title


class Comment(models.Model):
    """Append-only comment on a task.  No edit or delete is permitted."""

    task       = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author     = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    body       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.task}"
