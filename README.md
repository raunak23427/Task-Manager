# TaskFlow 🚀

Hey! Welcome to TaskFlow. I built this multi-user task management application using Django and MySQL. The goal was to create a clean, structured workspace for managing projects and collaborating, but more importantly, I wanted to focus on getting the backend architecture right—specifically around secure permissions, efficient ORM queries, and preventing N+1 database issues.

Plus, I gave the frontend a modern SaaS-inspired UI because a good project shouldn't have to look like a standard bootstrap template.

---

## 🎮 Demo: How it Works

To get a feel for how the app flows, here is the core user loop:

1. **Creating the Workspace**: You register/log in and arrive at your personal Dashboard. From here, you can create a new Project (e.g., "Q3 Launch"). As the creator, you are the **Owner**.
2. **Fleshing it out**: Inside the project, you start adding Tasks. You set priorities, due dates, and statuses. 
3. **Delegation**: You assign one of the tasks to your teammate, Bob. 
4. **The Member Experience**: Bob logs in. He doesn't own the project, so he can't randomly delete it or edit the project details. However, because he's assigned to a task, he is a **Member**. He can view the project, check his task, and drop a comment ("I'm starting this today!").
5. **Tracking Progress**: Back on your Dashboard, you can see real-time status counts, spot overdue tasks immediately, and even click the quick-complete circle on a task to mark it as done right from the home screen. This triggers a silent background POST request to keep the database in sync perfectly without reloading the page.

---

## ✨ Features & Permissions

### Core Functionality
- **Auth**: Standard Django auth (login, registration, logout, protected routes).
- **Projects & Tasks**: Full CRUD for projects and tasks. Tasks track Status (To Do, In Progress, Done), Priority, and Due Dates.
- **Collaboration**: Append-only commenting system for task discussion.
- **Interactive Dashboard**: Aggregated stats, overdue task alerts, and quick-completion UI.

### Permission Model (Strict Backend Enforcement)
I wanted to make sure security wasn't just a frontend illusion. If you try to bypass the UI and hit an endpoint you shouldn't, Django will block you with an HTTP `403 Forbidden`.

| Action | Project Owner | Project Member |
|--------|---------------|----------------|
| View project / tasks | Yes | Yes |
| Edit / Delete project | Yes | **No** |
| Create / Edit / Delete task | Yes | **No** |
| Add a comment | Yes | Yes |

*(A user automatically becomes a "Member" if they are assigned to at least one task in the project).*

---

## 🛠 Under the Hood

### Tech Stack
- **Backend**: Python 3.9+, Django 4.2 LTS
- **Database**: MySQL 8.0
- **Frontend**: Vanilla HTML/CSS/JS (Custom CSS variables, no heavy frameworks). Typography by Inter.

### Database Optimizations
I spent a good amount of time ensuring the database isn't doing unnecessary work:

1. **N+1 Query Prevention**: Hitting the DB in a loop is a classic mistake. I heavily used `select_related()` (for foreign keys like project and assigned user) and `prefetch_related()` (for reverse relations like comments) to fetch everything in large, efficient batches.
2. **Aggregation**: Instead of pulling all tasks into Python just to count them, I used Django's `.annotate(Count('id'))` to let MySQL do the heavy lifting for project status counts.
3. **Custom QuerySets**: I wrote a custom manager method `Task.objects.overdue()` to cleanly filter tasks that have missed their due date and aren't marked as "Done".
4. **Composite Indexing**: Added a composite index on `(status, due_date)` in the MySQL database to speed up the overdue task queries and dashboard rendering.

---

## 🚀 Getting Started Locally

Want to spin this up on your own machine? Here is the step-by-step:

### 1. Database Setup
Make sure you have MySQL 8.0 running. Open your MySQL CLI and run:
```sql
CREATE DATABASE taskmanager;
CREATE USER 'taskuser'@'localhost' IDENTIFIED BY 'taskpass';
GRANT ALL PRIVILEGES ON taskmanager.* TO 'taskuser'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Install Dependencies
Clone the repo, set up a virtual environment, and install the requirements:
```bash
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory (use `.env.example` as a guide) so Django can connect to your local MySQL instance.

### 4. Migrate & Seed
Set up the tables and load some dummy data to play with:
```bash
python manage.py migrate
python seed_demo.py
```
*(The seeder creates users like `alice` and `bob` with the password `password123`, plus an `admin` account).*

### 5. Run the Server
```bash
python manage.py runserver
```
Head over to `http://127.0.0.1:8000/` and you're good to go!

---

## 🧪 Testing

I wrote 46 automated tests covering models, views, forms, and all the permission edge cases. You can run the test suite to verify everything is working:

```bash
python manage.py test tasks --verbosity=2
```

---
*Built with coffee and late nights as a deep dive into Django architecture.*
