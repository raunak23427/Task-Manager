"""
Custom QuerySet and Manager for the Task model.

Centralises reusable query logic so views stay thin and
the same filters can be composed freely across views.
"""

from datetime import date

from django.db import models


class TaskQuerySet(models.QuerySet):
    """Reusable, composable queryset methods for the Task model."""

    def overdue(self):
        """
        Return tasks where due_date is strictly in the past and status is not Done.

        Conditions:
          - due_date < today   (strict; tasks due today are NOT overdue)
          - status != 'DONE'

        NULL due_date is intentionally excluded: a task with no due date cannot
        be overdue. Django's ORM omits NULLs from range comparisons automatically.

        SQL produced (approximately):
            SELECT ... FROM tasks_task
            WHERE due_date < CURDATE()
              AND NOT (status = 'DONE' AND status IS NOT NULL)

        The composite index idx_task_status_due_date on (status, due_date)
        accelerates this query — see QUERIES.md §D for EXPLAIN output.
        """
        return self.exclude(status="DONE").filter(due_date__lt=date.today())

    def for_user(self, user):
        """Tasks assigned to a given user."""
        return self.filter(assigned_to=user)

    def for_project(self, project):
        """Tasks belonging to a given project."""
        return self.filter(project=project)


class TaskManager(models.Manager):
    """Default manager for Task; returns TaskQuerySet instances."""

    def get_queryset(self):
        return TaskQuerySet(self.model, using=self._db)

    def overdue(self):
        """Shortcut: Task.objects.overdue()"""
        return self.get_queryset().overdue()
