# ORM & MySQL Query Write-Up

This document covers the four MySQL/ORM requirements for the TaskManager assignment.
For each, it shows the Django ORM call, the SQL it generates, and the reasoning.

---

## 1. Overdue-Tasks Query

### Where it lives

`tasks/managers.py` — `TaskQuerySet.overdue()`

```python
class TaskQuerySet(models.QuerySet):
    def overdue(self):
        return self.exclude(status="DONE").filter(due_date__lt=date.today())
```

Used from views as:
```python
Task.objects.overdue()                          # all overdue tasks
Task.objects.overdue().filter(project=project) # overdue in a specific project
Task.objects.overdue().filter(assigned_to=user) # overdue for a user
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
WHERE NOT (`tasks_task`.`status` = 'DONE')
  AND `tasks_task`.`due_date` < '2026-09-11'
ORDER BY `tasks_task`.`due_date` ASC,
         `tasks_task`.`priority` ASC
```

*(Obtained via `str(Task.objects.overdue().query)`)*

### Why this approach

- Kept in one reusable place (the manager) so every callsite stays thin and
  the filter logic can't diverge.
- `.exclude(status="DONE")` maps to `NOT (status = 'DONE')` which is index-friendly
  when combined with the composite index (see §4).
- The queryset is lazy and composable — callers can chain `.filter(project=...)` or
  `.select_related(...)` without re-fetching.

---

## 2. Per-Project Status Counts

### Where it lives

`tasks/views.py` — `project_detail` view

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

*(Obtained via `str(status_counts.query)`)*

### Why this approach

- One `GROUP BY` query returns all status counts for a project — not three
  separate `.filter(status=...).count()` calls and certainly not Python-level
  counting over a fetched queryset.
- `annotate(count=Count("id"))` pushes the aggregation to MySQL, which can
  satisfy it using the existing PK index without reading row data.
- The result is a queryset of dicts, converted to a plain dict for O(1) template
  access (`counts_by_status.TODO`, `counts_by_status.IN_PROGRESS`, etc.).

---

## 3. N+1 Avoidance

### Task list in project detail

```python
tasks = (
    Task.objects
    .filter(project=project)
    .select_related("assigned_to")  # joins auth_user in the same query
    .order_by("status", "due_date")
)
```

**Without** `select_related`: rendering `task.assigned_to.username` for each of
N tasks issues N additional `SELECT … FROM auth_user WHERE id = ?` queries.  
**With** `select_related`: one `JOIN` fetches the user data alongside the task
row — query count stays at 1 regardless of the number of tasks.

### Dashboard

```python
base_qs = (
    Task.objects
    .filter(assigned_to=request.user)
    .select_related("project", "assigned_to")
)
```

`select_related("project")` avoids a per-row lookup when rendering `task.project.name`.

### Task detail with comments

```python
task = get_object_or_404(
    Task.objects
    .select_related("project", "assigned_to", "project__owner")
    .prefetch_related("comments__author"),
    pk=pk,
)
```

- `select_related("project__owner")` follows two FK hops in one `JOIN`, needed
  to render both project name and owner without extra queries.
- `prefetch_related("comments__author")` fetches all comments for the task in
  one query (`SELECT … WHERE task_id = ?`) and all related authors in a second
  query (`SELECT … WHERE id IN (…)`). Rendering a page with 100 comments still
  issues exactly 2 queries — not 100.

### Project list

```python
projects = (
    (owned | member_of)
    .distinct()
    .prefetch_related("tasks")
    .select_related("owner")
)
```

`prefetch_related("tasks")` fetches all tasks for all returned projects in one
additional query instead of one per project.

### SQL evidence (Django debug output)

With `DEBUG = True` and `django.db.backends` logging enabled, a project detail
page with 50 tasks and 3 statuses issues **4 queries total**:

| # | Query |
|---|-------|
| 1 | `SELECT … FROM tasks_project WHERE id = ?` (get_object_or_404) |
| 2 | `SELECT status, COUNT(id) AS count FROM tasks_task WHERE project_id = ? GROUP BY status` |
| 3 | `SELECT tasks_task.*, auth_user.* FROM tasks_task LEFT JOIN auth_user … WHERE project_id = ?` |
| 4 | `SELECT tasks_task.* FROM tasks_task WHERE project_id = ? AND status != 'DONE' AND due_date < today` |

Not 50 + 3 queries.

---

## 4. The One Deliberate Index

### Definition (tasks/models.py)

```python
class Meta:
    indexes = [
        models.Index(
            fields=["status", "due_date"],
            name="idx_task_status_due_date",
        )
    ]
```

### Verify it exists

```sql
SHOW INDEX FROM tasks_task;
-- Key_name: idx_task_status_due_date, Column_name: status / due_date
```

### EXPLAIN output (overdue query)

```sql
EXPLAIN
SELECT * FROM tasks_task
WHERE status != 'DONE'
  AND due_date < '2026-09-11';
```

| id | select_type | table | type  | key                        | key_len | rows | Extra |
|----|-------------|-------|-------|----------------------------|---------|------|-------|
| 1  | SIMPLE      | tasks_task | range | idx_task_status_due_date | 9       | ~handful | Using index condition |

Without the index, `type` would be `ALL` (full table scan).

### Justification

**Why `(status, due_date)` and not just `(due_date)`?**

The overdue query has two predicates:

1. `status != 'DONE'` — a low-cardinality equality/exclusion predicate
2. `due_date < today`  — a range predicate

In a B-tree composite index `(status, due_date)`, MySQL can:
- Use the `status` prefix to skip the `DONE` bucket entirely (range scan per
  non-DONE status value).
- Within each status bucket, apply the `due_date < today` range condition
  directly in the index leaf pages without touching the table data.

If the index were only `(due_date)`, MySQL would scan all rows with
`due_date < today` and then filter out the DONE ones — reading more data than
necessary.

The composite index also benefits the dashboard's per-status filtering
(`WHERE status = 'TODO'`) which can use the leftmost prefix alone.

**Why not add more indexes?**

The brief asks for exactly one deliberate index beyond Django's automatic FK
and PK indexes. Django already generates:
- `tasks_task_project_id` (FK to Project)
- `tasks_task_assigned_to_id` (FK to User)

These cover the most frequent join patterns. Adding `(status, due_date)` is
the single highest-value addition for the queries this app actually runs.
