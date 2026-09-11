"""
Custom QuerySet and Manager for the Task model.

Centralises reusable query logic so views stay thin and
the same filters can be composed freely.
"""

from datetime import date

from django.db import models


class TaskQuerySet(models.QuerySet):
    """Reusable, composable queryset methods for Task."""

    def overdue(self):
        """
        Return tasks where due_date is in the past and status is not Done.

        A single SQL query:
            SELECT ... FROM tasks_task
            WHERE due_date < CURDATE() AND status != 'DONE'

        The composite index idx_task_status_due_date on (status, due_date)
        lets MySQL skip the DONE bucket entirely and scan only the range
        predicate on due_date for the remaining statuses.
        """
        return self.exclude(status="DONE").filter(due_date__lt=date.today())

    def for_user(self, user):
        """Tasks assigned to a given user."""
        return self.filter(assigned_to=user)

    def for_project(self, project):
        """Tasks belonging to a given project."""
        return self.filter(project=project)


class TaskManager(models.Manager):
    def get_queryset(self):
        return TaskQuerySet(self.model, using=self._db)

    def overdue(self):
        return self.get_queryset().overdue()
