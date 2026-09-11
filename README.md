# TaskManager

A multi-user task manager built with **Django 6.1** and **MySQL 8.0**, as a take-home
assignment for Race AI. The project demonstrates correct data modelling, strict
ownership-based permissions enforced at the view layer, and efficient ORM queries
(no N+1 queries, deliberate composite index, annotate-based aggregation).

---

## Stack

| Component | Version |
|-----------|---------|
| Python    | 3.11+   |
| Django    | 6.1     |
| MySQL     | 8.0     |
| mysqlclient | 2.2.x |
| python-dotenv | 1.0.x |

---

## Local Setup

### 1. Prerequisites

- Python 3.11 or higher
- Docker + Docker Compose (for MySQL)
- Git

### 2. Clone the repository

```bash
git clone <your-repo-url>
cd taskmanager
```

### 3. Create a virtual environment and install dependencies

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Start MySQL with Docker Compose

```bash
docker compose up -d
```

This starts a MySQL 8.0 container with:
- **Database**: `taskmanager`
- **User**: `taskuser` / **Password**: `taskpass`
- **Port**: `3306` (bound to localhost)

Wait ~10 seconds for the container to be ready. You can verify with:

```bash
docker compose logs db
# look for: ready for connections
```

### 5. Configure environment variables

Copy the template and edit if needed (defaults match the Docker Compose config):

```bash
cp .env.example .env
```

The `.env` file:

```
SECRET_KEY=django-insecure-replace-this-with-a-long-random-string
DEBUG=True
DB_NAME=taskmanager
DB_USER=taskuser
DB_PASSWORD=taskpass
DB_HOST=127.0.0.1
DB_PORT=3306
```

### 6. Run migrations

```bash
python manage.py migrate
```

This creates all tables including the composite index `idx_task_status_due_date`
on `(status, due_date)` in the `tasks_task` table.

### 7. Create a superuser (optional, for the admin panel)

```bash
python manage.py createsuperuser
```

### 8. Start the development server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Running Without Docker

If you already have a MySQL 8.0 instance, create the database and user manually:

```sql
CREATE DATABASE taskmanager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'taskuser'@'localhost' IDENTIFIED BY 'taskpass';
GRANT ALL PRIVILEGES ON taskmanager.* TO 'taskuser'@'localhost';
FLUSH PRIVILEGES;
```

Then update `.env` with your connection details and run `python manage.py migrate`.

---

## Application Structure

```
taskmanager/        — Django project settings & root URLs
accounts/           — Auth: register, login, logout
tasks/              — Core: Project, Task, Comment models + all views
  managers.py       — Custom TaskQuerySet with overdue() method
  models.py         — Data models with TextChoices and composite index
  views.py          — Views with _require_owner / _require_member permission guards
  forms.py          — ModelForms for Project, Task, Comment
templates/
  base.html         — Navbar + layout wrapper
  accounts/         — Login and Register pages
  tasks/            — Dashboard, project/task CRUD, comments
static/css/style.css — Dark-theme stylesheet
docker-compose.yml
requirements.txt
.env.example
QUERIES.md          — ORM query write-up
```

---

## Features

- **Register / Log in / Log out** via Django's built-in auth
- **Projects**: Create, list, view, edit, delete (owner-only for edit/delete)
- **Tasks**: Full CRUD within projects (owner-only for create/edit/delete); assignable to any user
- **Comments**: Append-only comments on tasks, visible to any project member
- **Dashboard**: Logged-in user's tasks in three kanban columns (To Do / In Progress / Done) plus an **Overdue** banner
- **Project detail**: Per-project task counts by status + overdue task list

---

## Permissions Design

Ownership checks are enforced **at the view layer**, not just by hiding buttons in the template.  
A direct `POST` from a non-owner to any mutating URL receives an **HTTP 403 PermissionDenied** response.

```python
# tasks/views.py — used in every mutating view
def _require_owner(project, user):
    if project.owner != user:
        raise PermissionDenied   # → 403, regardless of the UI

def _require_member(project, user):
    if not project.is_member(user):
        raise PermissionDenied
```

"Member" is defined as: the project owner **or** any user who has been `assigned_to` at least one task in the project.  
This keeps the schema minimal (no extra M2M table) while satisfying the brief.

---

## Design Assumptions

1. **Membership is implicit** — no separate `ProjectMember` table; see above.
2. **Any authenticated user can be assigned a task** — the assignee dropdown shows all registered users.
3. **Comment authors must be project members** — the same `_require_member` check guards the comment POST.
4. **Django 6.1 is used** — the latest stable release at submission time; API is fully compatible with 4.2 LTS.

---

## ORM Write-Up

See **[QUERIES.md](QUERIES.md)** for the full write-up covering all four MySQL/ORM requirements:
the overdue-tasks query, per-project status counts, N+1 avoidance, and the composite index justification.
