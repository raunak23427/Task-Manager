# Django Task Manager

A multi-user task management application built with **Django 4.2** and **MySQL 8.0**,
demonstrating correct data modelling, strict server-side permission enforcement,
and efficient ORM query design.

---

## Features

- **Authentication** — register, log in, log out (Django built-in auth)
- **Projects** — full CRUD; only the project owner can edit or delete
- **Tasks** — full CRUD within projects; assignable to any user; only the project owner can create, edit, or delete
- **Comments** — append-only comments on tasks; any project member can comment
- **Dashboard** — logged-in user's tasks grouped by status (To Do / In Progress / Done) with an **Overdue** section
- **Per-project status counts** — efficient `annotate + Count` query
- **Membership control** — non-members cannot access projects or tasks by guessing IDs (IDOR protected)

---

## Tech Stack

| Component    | Version |
|--------------|---------|
| Python       | 3.11+   |
| Django       | 4.2.x (LTS) |
| MySQL        | 8.0     |
| mysqlclient  | 2.2.x   |
| python-dotenv| 1.0.x   |

---

## Project Structure

```
taskmanager/            — Django project settings & root URLs
accounts/               — Auth app: register, login, logout
tasks/                  — Core app
  managers.py           — Custom TaskQuerySet (overdue() and helpers)
  models.py             — Project, Task (TextChoices, composite index), Comment
  views.py              — Views with _require_owner / _require_member guards
  forms.py              — ModelForms for Project, Task, Comment
  admin.py              — Admin registration with useful list_display/filters
  tests.py              — 46 automated tests covering permissions, queries, IDOR
  migrations/           — Database migrations
templates/
  base.html             — Navbar + layout
  accounts/             — login.html, register.html
  tasks/                — dashboard, project CRUD, task CRUD, comments
static/css/style.css    — Dark-theme CSS (minimal, functional)
docker-compose.yml      — MySQL 8.0 container
requirements.txt
.env.example
README.md
QUERIES.md              — ORM/SQL write-up for all four requirements
```

---

## Requirements

- Python 3.11 or higher
- pip
- Docker + Docker Compose **or** a local MySQL 8.0 installation
- Git

---

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd taskmanager
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
SECRET_KEY=replace-with-a-long-random-string
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DB_NAME=taskmanager
DB_USER=taskuser
DB_PASSWORD=taskpass
DB_HOST=127.0.0.1
DB_PORT=3306
DB_TEST_NAME=test_taskmanager
```

### 4. Start MySQL

**Option A — Docker Compose (recommended)**

```bash
docker compose up -d
```

This starts MySQL 8.0 with the credentials in `.env.example` (matching the defaults).
Wait ~10 seconds, then verify: `docker compose logs db | tail -5`

**Option B — Existing MySQL instance**

Create the database and user manually:

```sql
CREATE DATABASE IF NOT EXISTS taskmanager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS test_taskmanager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'taskuser'@'localhost' IDENTIFIED BY 'taskpass';
GRANT ALL PRIVILEGES ON taskmanager.* TO 'taskuser'@'localhost';
GRANT ALL PRIVILEGES ON test_taskmanager.* TO 'taskuser'@'localhost';
GRANT CREATE ON *.* TO 'taskuser'@'localhost';
FLUSH PRIVILEGES;
```

Update `.env` with your host/port/password.

### 5. Run migrations

```bash
python manage.py migrate
```

This creates all tables including the composite index `idx_task_status_due_date`
on `(status, due_date)` in `tasks_task`.

Verify the index:

```sql
SHOW INDEX FROM tasks_task WHERE Key_name = 'idx_task_status_due_date';
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000**

---

## Environment Variables

| Variable      | Description                                 | Default        |
|---------------|---------------------------------------------|----------------|
| `SECRET_KEY`  | Django secret key — keep this private       | insecure default |
| `DEBUG`       | `True` for development, `False` in production | `True`       |
| `ALLOWED_HOSTS` | Comma-separated allowed hostnames         | `127.0.0.1,localhost` |
| `DB_NAME`     | MySQL database name                         | `taskmanager`  |
| `DB_USER`     | MySQL username                              | `taskuser`     |
| `DB_PASSWORD` | MySQL password                              | `taskpass`     |
| `DB_HOST`     | MySQL host                                  | `127.0.0.1`    |
| `DB_PORT`     | MySQL port                                  | `3306`         |
| `DB_TEST_NAME`| Test database name (for `manage.py test`)   | `test_taskmanager` |

---

## Usage

### Registration & Login
- Visit `/accounts/register/` to create an account.
- Log in at `/accounts/login/`.

### Projects
- View all visible projects at `/projects/`.
- Create a new project — you become its **owner**.
- Only the owner can edit or delete a project.

### Tasks
- Open a project to see its tasks.
- Only the project owner can create, edit, or delete tasks.
- Tasks can be assigned to any registered user.

### Assignment
- When editing a task, select any user from the **Assigned To** dropdown.
- Assigned users can view the task and add comments but cannot edit/delete it.

### Comments
- Open any task you can view.
- Add a comment via the form at the bottom.
- Comments are append-only — no editing or deleting.

### Dashboard
- The home page (`/`) shows your tasks grouped by status.
- An **Overdue** banner at the top highlights tasks past their due date.

---

## Permissions

| Action                    | Who can do it                      |
|---------------------------|------------------------------------|
| View project              | Owner or any user assigned to a task in the project |
| Create / edit / delete project | **Owner only** |
| Create / edit / delete tasks | **Owner only** (of the project) |
| View task                 | Any project member                 |
| Assign task to user       | Owner (when creating/editing task) |
| Add comment               | Any project member                 |

**All permission checks are enforced at the server/view layer.**
A direct HTTP POST from a non-owner returns **HTTP 403 Forbidden** — not just
a hidden button in the template.

---

## ORM / Database Design

### Overdue Query
A custom `TaskQuerySet.overdue()` method in `tasks/managers.py` filters
`due_date < today AND status != DONE` in a single composable query.

### Status Counts
`annotate(count=Count('id')).values('status')` produces one `GROUP BY` SQL
query — no Python counting, no multiple queries.

### N+1 Prevention
- `select_related` is used for forward ForeignKey access (task→project, task→assigned_to, comment→author)
- `prefetch_related` is used for reverse/many relations (task→comments, project→tasks)

### Custom Index
One deliberate composite index `idx_task_status_due_date` on `(status, due_date)`
supports the overdue query and dashboard status filters.

See **[QUERIES.md](QUERIES.md)** for full ORM code, generated SQL, and justification.

---

## Testing

```bash
python manage.py test tasks --verbosity=2
```

The test suite includes **46 tests** covering:

- Auth (register, login, logout, unauthenticated redirect)
- Project permissions (owner can CRUD, non-owner gets 403 on direct POST)
- Task permissions (owner only; assigned user cannot edit/delete)
- Project membership / IDOR (stranger gets 403, not 200)
- Comment permissions (member can comment, stranger gets 403)
- Overdue query edge cases (past/future/done/no-date/today)
- Status counts (correctness, context presence, project isolation)
- Dashboard (grouping by status, overdue section)

All 46 tests pass.

---

## Design Decisions & Assumptions

1. **Membership is implicit** — no separate `ProjectMember` model. A member is
   the owner OR any user assigned to at least one task in the project.
2. **Any registered user can be assigned** to a task — the assignee dropdown
   shows all users, keeping the model simple.
3. **Django 4.2 LTS** is used for MySQL 8.0.x compatibility.
   Django 6.x requires MySQL 8.4+.
4. **`ALLOWED_HOSTS`** is read from the environment variable — set to
   `127.0.0.1,localhost` by default for local development. Set it appropriately
   for production.
