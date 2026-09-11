# TaskFlow

TaskFlow is a multi-user task management application built with Django and MySQL. It provides a structured workspace for managing projects, assigning tasks, tracking progress, and collaborating through comments.

The project focuses on clean backend architecture, secure permission enforcement, efficient Django ORM queries, and a modern productivity-focused user interface. I built this to demonstrate a complete Django workflow with a polished, SaaS-inspired frontend because a good backend project shouldn't have to look like a standard bootstrap template.

---

## Demo: How it Works

To get a feel for how the app flows, here is the core user loop:

1. **Creating the Workspace**: You register or log in and arrive at your personal Dashboard. From here, you can create a new Project (e.g., "Q3 Launch"). As the creator, you are the **Owner**.
2. **Fleshing it out**: Inside the project, you start adding Tasks. You set priorities, due dates, and statuses. 
3. **Delegation**: You assign one of the tasks to your teammate, Bob. 
4. **The Member Experience**: Bob logs in. He doesn't own the project, so he can't randomly delete it or edit the project details. However, because he's assigned to a task, he is a **Member**. He can view the project, check his task, and drop a comment ("I'm starting this today!").
5. **Tracking Progress**: Back on your Dashboard, you can see real-time status counts, spot overdue tasks immediately, and even click the quick-complete circle on a task to mark it as done right from the home screen. This triggers a silent background POST request to keep the database in sync perfectly without reloading the page.

---

## Features

### Authentication

- User registration
- User login
- User logout
- Django's built-in authentication system
- Automatic login after registration
- Protected application views for authenticated users

### Projects

Users can:

- Create projects
- View their projects
- View projects where they are members
- Edit projects they own
- Delete projects they own

### Tasks

Each project can contain multiple tasks.

Tasks support:

- Title
- Description
- Status
- Priority
- Due date
- Project association
- User assignment

Available statuses:

- To Do
- In Progress
- Done

Available priorities:

- Low
- Medium
- High

### Task Collaboration

Users who are members of a project can:

- View project tasks
- Open task details
- Add comments

Comments are append-only and cannot be edited or deleted.

### Dashboard

The dashboard provides an overview of the authenticated user's tasks.

It includes:

- To Do tasks
- In Progress tasks
- Completed tasks
- Overdue tasks
- Task statistics
- Quick task completion

Tasks can be marked as completed directly from the dashboard.

### Permissions

TaskFlow enforces permissions at the Django backend/view layer.

The permission model is:

| Action | Project Owner | Project Member |
|--------|---------------|----------------|
| View project | Yes | Yes |
| Edit project | Yes | No |
| Delete project | Yes | No |
| Create task | Yes | No |
| Edit task | Yes | No |
| Delete task | Yes | No |
| View task | Yes | Yes |
| Add comment | Yes | Yes |

A project member is a user assigned to at least one task within that project.

Unauthorized edit and delete requests are rejected with an HTTP `403 Forbidden` response.

---

## Technology Stack

### Backend

- Python 3
- Django 4.2 LTS

### Database

- MySQL 8.0

### Frontend

- HTML5
- CSS3
- Vanilla JavaScript
- Custom CSS variables
- Responsive layouts
- CSS transitions and micro-interactions

### Typography

- Inter

---

## Project Structure

```text
taskmanager/
│
├── taskmanager/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── accounts/
│   ├── views.py
│   ├── urls.py
│   └── templates/
│
├── tasks/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   ├── managers.py
│   └── templates/
│
├── templates/
│   └── base.html
│
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── manage.py
├── seed_demo.py
├── README.md
└── QUERIES.md
```

---

## Data Model

TaskFlow uses three core application models.

```text
User
 │
 ├── owns ──> Project
 │
 └── assigned to ──> Task
                       │
                       └── has ──> Comment
```

### Project

A project belongs to an owner and contains multiple tasks.

### Task

A task belongs to a project and can optionally be assigned to a user.

### Comment

A comment belongs to a task and records its author and creation time.

---

## Database Optimization

The project demonstrates efficient Django ORM usage and includes several query optimizations.

### Overdue Tasks

A custom queryset method is used to retrieve overdue tasks while excluding completed tasks.

```python
Task.objects.overdue()
```

The query checks for:

* A due date before today's date
* A status other than `DONE`

---

### Project Status Counts

Task counts by status are calculated using Django's `annotate()` and `Count()` functionality rather than counting tasks in Python.

```python
Task.objects.filter(
    project=project
).values(
    'status'
).annotate(
    count=Count('id')
)
```

This allows the database to perform the aggregation efficiently.

---

### N+1 Query Prevention

Related objects are loaded efficiently using:

```python
select_related()
```

and

```python
prefetch_related()
```

Examples include:

```python
Task.objects.filter(
    project=project
).select_related('assigned_to')
```

and:

```python
Task.objects.select_related(
    'project',
    'assigned_to'
).prefetch_related(
    'comments__author'
)
```

This reduces unnecessary database queries when displaying related objects.

---

### Composite Database Index

The `Task` model includes a composite index on:

```text
(status, due_date)
```

Index name:

```text
idx_task_status_due_date
```

This index supports queries involving task status and due dates, including overdue-task filtering.

---

## UI / UX

TaskFlow uses a modern productivity-app inspired interface.

### Design System

* **Primary:** `#FFB81C`
* **Background:** `#F5F2EA`
* **Sidebar:** `#292827`
* Rounded cards and controls
* Soft shadows
* Clean typography
* Minimal interface
* Smooth hover effects
* Fast micro-interactions
* Responsive layouts

The interface is designed to provide a polished task-management experience while keeping the application functional and easy to navigate.

---

## Setup

### Prerequisites

Make sure the following are installed:

* Python 3.9+
* Django 4.2
* MySQL 8.0
* Git

---

## 1. Clone the Repository

```bash
git clone <your-repository-url>
cd taskmanager
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure MySQL

Create the database and user:

```sql
CREATE DATABASE taskmanager;

CREATE USER 'taskuser'@'localhost'
IDENTIFIED BY 'taskpass';

GRANT ALL PRIVILEGES
ON taskmanager.*
TO 'taskuser'@'localhost';

FLUSH PRIVILEGES;
```

---

## 5. Configure Environment Variables

Create a `.env` file based on `.env.example`.

Example:

```env
DB_NAME=taskmanager
DB_USER=taskuser
DB_PASSWORD=taskpass
DB_HOST=localhost
DB_PORT=3306
```

Do not commit your actual `.env` file to GitHub.

---

## 6. Run Migrations

```bash
python manage.py migrate
```

---

## 7. Create an Admin User

```bash
python manage.py createsuperuser
```

Follow the prompts to create the Django administrator account.

---

## 8. Seed Demo Data

The project includes a demo seed script for quickly creating sample users, projects, and tasks.

```bash
python seed_demo.py
```

---

## Demo Accounts

The project includes three demo profiles for testing and demonstration:

| Username | Password | Role |
|---|---|---|
| `alice` | `password123` | Project Owner |
| `bob` | `password123` | Project Member |
| `admin` | `password123` | Administrator |

### Demo Permission Flow

Use `alice` to demonstrate project and task management:

- Create projects
- Create tasks
- Assign tasks to `bob`
- Edit and delete owned projects and tasks

Use `bob` to demonstrate member permissions:

- View projects where assigned
- View assigned tasks
- Add comments
- Attempt restricted edit/delete operations and verify that Django returns `403 Forbidden`

Use `admin` to access the Django administration interface.

These credentials are for local development and demonstration only.

---

## 9. Start the Development Server

```bash
python manage.py runserver
```

Open the application at:

```text
http://127.0.0.1:8000/
```

---

## Testing

Run the Django test suite with:

```bash
python manage.py test tasks --verbosity=2
```

The tests cover areas including:

* Models
* Views
* Forms
* Authentication
* Permissions
* Task functionality

---

## Permission Testing

The permission system can be verified using two different users.

### Example

1. Log in as the project owner.
2. Create a project.
3. Create a task.
4. Assign the task to another user.
5. Log out.
6. Log in as the assigned member.
7. Open the project/task.
8. Add a comment.
9. Attempt to edit or delete the project/task directly.

The member should be able to view and comment but should receive:

```text
HTTP 403 Forbidden
```

when attempting unauthorized operations.

---

## Verification Checklist

Before submitting the project, verify:

* [ ] Registration works
* [ ] Login works
* [ ] Logout works
* [ ] Project creation works
* [ ] Project editing works
* [ ] Project deletion works
* [ ] Task creation works
* [ ] Task assignment works
* [ ] Task status changes work
* [ ] Task priority works
* [ ] Due dates work
* [ ] Comments work
* [ ] Overdue tasks appear correctly
* [ ] Project status counts are correct
* [ ] Members cannot edit projects
* [ ] Members cannot delete projects
* [ ] Members cannot create tasks
* [ ] Unauthorized requests return HTTP 403
* [ ] `select_related()` is used where appropriate
* [ ] `prefetch_related()` is used where appropriate
* [ ] Composite database index exists
* [ ] Tests pass
* [ ] `.env` is not committed

---

## Useful Django Commands

Run migrations:

```bash
python manage.py migrate
```

Create migrations:

```bash
python manage.py makemigrations
```

Create an admin account:

```bash
python manage.py createsuperuser
```

Run the development server:

```bash
python manage.py runserver
```

Run tests:

```bash
python manage.py test tasks
```

Open Django shell:

```bash
python manage.py shell
```

---

## Documentation

Additional information about the ORM implementation and database queries can be found in:

```text
QUERIES.md
```

The document explains:

* Overdue task queries
* Status aggregation
* `select_related()`
* `prefetch_related()`
* Composite indexes
* Query optimization reasoning

---

## Project Goal

TaskFlow was built to demonstrate a complete Django task-management workflow while focusing on:

* Correct relational data modeling
* Secure backend permission enforcement
* Efficient database queries
* N+1 query prevention
* Clean Django architecture
* Modern and responsive UI/UX

---

## License

This project is developed as an academic/project submission.
