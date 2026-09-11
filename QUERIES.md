# ORM & MySQL Query Documentation

This document covers the four MySQL/ORM requirements for the TaskManager assignment.
For each requirement it shows:
1. The Django ORM code
2. The SQL Django generates (from `str(queryset.query)`)
3. Why it is implemented this way

---

## A — Overdue Tasks Query

### Location
`tasks/managers.py` → `TaskQuerySet.overdue()`

### ORM Code

```python
# tasks/managers.py
class TaskQuerySet(models.QuerySet):
    def overdue(self):
        return self.exclude(status="DONE").filter(due_date__lt=date.today())
```

Called from views as:
```python
Task.objects.overdue()                           # all overdue tasks
Task.objects.overdue().filter(project=project)   # scoped to a project
Task.objects.overdue().filter(assigned_to=user)  # scoped to a user
```

### Generated SQL

```sql
SELECT `tasks_task`.`id`,
       `tasks_task`.`title`,
       `tasks_task`.`status`,
       `tasks_task`.`priority`,
       `tasks_task`.`due_date`,
       `tasks_task`.`project_id`,
       `tasks_task`.`assigned_to_id`,
       `tasks_task`.`created_at`
FROM `tasks_task`
WHERE NOT (`tasks_task`.`status` = 'DONE'
           AND `tasks_task`.`status` IS NOT NULL)
  AND `tasks_task`.`due_date` < '2026-09-11'
ORDER BY `tasks_task`.`due_date` ASC,
         `tasks_task`.`priority` ASC
```

*(Verified via `str(Task.objects.overdue().query)` in Django shell)*

### Why this approach

- **One reusable place**: the method lives on `TaskQuerySet` so every view
  (`dashboard`, `project_detail`) calls `Task.objects.overdue()` without
  duplicating the filter logic.
- **Composable**: returns a lazy queryset, so callers can chain
  `.filter(project=...)` or `.select_related(...)` without extra queries.
- **NULL safety**: `filter(due_date__lt=date.today())` automatically excludes
  rows where `due_date IS NULL` — tasks with no due date are never overdue.
- **Today is not overdue**: the condition is strict `<`, so a task due today
  is not considered overdue.

---

## B — Per-Project Status Counts

### Location
`tasks/views.py` → `project_detail` view

### ORM Code

```python
from django.db.models import Count

status_counts = (
    Task.objects
    .filter(project=project)
    .values("status")
    .annotate(count=Count("id"))
)
counts_by_status = {row["status"]: row["count"] for row in status_counts}
```

### Generated SQL

```sql
SELECT `tasks_task`.`status`,
       COUNT(`tasks_task`.`id`) AS `count`
FROM `tasks_task`
WHERE `tasks_task`.`project_id` = 1
GROUP BY `tasks_task`.`status`
```

*(Verified via `str(status_counts.query)` in Django shell)*

### Why this approach

- **One query**: `GROUP BY status` returns all status counts in a single
  round-trip to the database.
- **No Python counting**: the alternative — fetching all tasks and counting
  with `len([t for t in tasks if t.status == 'TODO'])` — is O(N) Python
  work and fetches all columns unnecessarily.
- **No three separate queries**: calling `.filter(status='TODO').count()`
  three times would issue three queries; `GROUP BY` does it in one.
- **Zero-safe**: projects with no tasks in a status simply don't appear in
  the result dict; the template uses `counts_by_status.get('TODO', 0)` which
  defaults to zero correctly.

---

## C — N+1 Query Avoidance

### Problem

When a list page renders N rows and each row accesses a related object
(e.g. `task.assigned_to.username`), Django issues N extra SQL queries —
one per row. This grows linearly and silently.

### Fix: `select_related` for forward ForeignKeys

`select_related` performs a SQL `JOIN` and fetches the related object in the
same query.

**Task list in project detail (task → assigned_to)**
```python
tasks = (
    Task.objects
    .filter(project=project)
    .select_related("assigned_to")   # JOIN auth_user in the same query
    .order_by("status", "due_date")
)
```

SQL (abbreviated):
```sql
SELECT tasks_task.*, auth_user.*
FROM tasks_task
LEFT OUTER JOIN auth_user ON tasks_task.assigned_to_id = auth_user.id
WHERE tasks_task.project_id = 1
```

**Dashboard (task → project)**
```python
base_qs = (
    Task.objects
    .filter(assigned_to=request.user)
    .select_related("project")
)
```

**Task detail (task → project → owner)**
```python
task = get_object_or_404(
    Task.objects
    .select_related("project", "assigned_to", "project__owner"),
    pk=pk,
)
```

### Fix: `prefetch_related` for reverse/many relations

`prefetch_related` issues a second query to fetch all related objects at once
using an `IN` clause, rather than one query per parent object.

**Task detail — comments + their authors**
```python
task = get_object_or_404(
    Task.objects
    .select_related("project", "assigned_to", "project__owner")
    .prefetch_related("comments__author"),
    pk=pk,
)
```

SQL (two queries instead of N+1):
```sql
-- Query 1: the task itself with JOINs
SELECT tasks_task.*, auth_user.*, tasks_project.*
FROM tasks_task
LEFT JOIN ...

-- Query 2: all comments for this task
SELECT tasks_comment.*, auth_user.*
FROM tasks_comment
JOIN auth_user ON tasks_comment.author_id = auth_user.id
WHERE tasks_comment.task_id = 42
```

**Project list — all tasks per project**
```python
projects = (
    Project.objects
    .filter(...)
    .select_related("owner")
    .prefetch_related("tasks")
)
```

### Result

| Page | Queries (without) | Queries (with) |
|------|-------------------|----------------|
| Project detail (50 tasks) | 1 + 50 | 4 (project, counts, tasks+assignees, overdue) |
| Task detail (20 comments) | 1 + 20 | 3 (task+joins, comments+authors, ─) |
| Dashboard (30 tasks) | 1 + 30 | 4 (3 status groups + overdue) |

---

## D — Database Index

### Definition

```python
# tasks/models.py — Task.Meta
indexes = [
    models.Index(
        fields=["status", "due_date"],
        name="idx_task_status_due_date",
    )
]
```

### Verify in MySQL

```sql
SHOW INDEX FROM tasks_task WHERE Key_name = 'idx_task_status_due_date';
```

Expected output:
```
Table       | Key_name                    | Column_name | Seq_in_index
tasks_task  | idx_task_status_due_date    | status      | 1
tasks_task  | idx_task_status_due_date    | due_date    | 2
```

### EXPLAIN for the overdue query

```sql
EXPLAIN
SELECT * FROM tasks_task
WHERE NOT (status = 'DONE')
  AND due_date < '2026-09-11';
```

| id | select_type | table      | type  | key                      | rows | Extra                 |
|----|-------------|------------|-------|--------------------------|------|-----------------------|
| 1  | SIMPLE      | tasks_task | range | idx_task_status_due_date | ~few | Using index condition |

`type = range` means MySQL performs an index range scan instead of a full
table scan (`ALL`). Without the index, `type` would be `ALL`.

### Why `(status, due_date)` specifically

The overdue query has two predicates:

1. `status != 'DONE'` — equality/exclusion on a low-cardinality column
2. `due_date < today` — a range predicate

In a composite B-tree index `(status, due_date)`:
- MySQL uses the **leftmost prefix** (`status`) to skip the `DONE` partition
  entirely, scanning only `TODO` and `IN_PROGRESS` status values.
- Within each status bucket, it applies the **range condition** on `due_date`
  directly from index leaf pages, without touching the main table rows.

A single-column `(due_date)` index would scan all rows with
`due_date < today` (including DONE tasks) and then filter — reading more rows
than necessary.

The composite index also benefits the dashboard's per-status filter
(`WHERE status = 'TODO' AND assigned_to_id = ?`) via the leftmost prefix.

### Why exactly one index

Django automatically creates B-tree indexes for:
- Primary keys (`id`)
- All `ForeignKey` columns (`project_id`, `assigned_to_id`)

These cover the most frequent join patterns.
`(status, due_date)` is the single highest-value addition for the queries
this application actually runs in production use.
Adding more indexes would increase write overhead without a clear read benefit
for the current query set.
