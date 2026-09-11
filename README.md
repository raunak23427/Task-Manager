# TaskFlow

TaskFlow is a premium, modern Django-based Task Management application designed with a polished SaaS productivity interface. It allows users to manage projects, track tasks through various statuses, assign work to team members, and collaborate via comments.

## ✨ Features

- **Premium UI/UX:** A carefully crafted frontend featuring soft shadows, rounded tactile cards, a warm color palette, and smooth micro-interactions.
- **Projects & Tasks:** Create projects and populate them with tasks. Track task status (To Do, In Progress, Done), priority, and due dates.
- **Interactive Dashboards:** A dynamic dashboard displaying task statistics, overdue alerts, and organized task lists.
- **Quick Complete:** Seamlessly mark tasks as completed from the dashboard with smooth frontend animations synchronized perfectly with secure backend POST requests.
- **Collaboration:** Add comments to tasks to keep the team informed.
- **Robust Permissions:** Strict backend access controls. Only project owners can create, edit, or delete projects and tasks. Members can view and comment.
- **Optimized Queries:** Efficient ORM usage with `select_related` and `prefetch_related` to prevent N+1 queries.

## 🛠️ Technology Stack

- **Backend:** Python 3, Django 4.2 LTS
- **Database:** MySQL 8.0 (utilizing optimized composite indexes)
- **Frontend:** Vanilla HTML5, CSS3 (Custom Properties/Variables), and Vanilla JavaScript (No heavy frameworks required)
- **Typography:** Inter (Google Fonts)

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- MySQL 8.0+

### 1. Database Setup
Ensure your local MySQL server is running. Log into MySQL as root and create the database and user:

```sql
CREATE DATABASE taskmanager;
CREATE USER 'taskuser'@'localhost' IDENTIFIED BY 'taskpass';
GRANT ALL PRIVILEGES ON taskmanager.* TO 'taskuser'@'localhost';
FLUSH PRIVILEGES;
```
*(Note: The application is configured to use `taskuser` with password `taskpass` and connects to the `taskmanager` database on `localhost:3306`.)*

### 2. Environment Setup

Clone the repository and install the dependencies (typically just Django and the MySQL client):

```bash
pip install -r requirements.txt
```
*(If you don't have a requirements.txt, ensure you install: `pip install Django==4.2 mysqlclient`)*

### 3. Migrations & Seeding

Run the Django migrations to set up the database schema:

```bash
python manage.py migrate
```

To quickly populate the database with sample users, projects, and tasks, run the included seed script:

```bash
python seed_demo.py
```
*This will create demo accounts such as `alice` and `bob` (password: `password123`) and an `admin` account.*

### 4. Running the Server

Start the development server:

```bash
python manage.py runserver
```

Navigate to `http://127.0.0.1:8000` in your web browser to start using TaskFlow!

## 🧪 Testing

The project includes a comprehensive test suite (46 passing tests) covering models, views, forms, and permission logic.

Run the tests using:
```bash
python manage.py test tasks --verbosity=2
```

## 🎨 UI/UX Design System

The frontend was recently redesigned to match premium productivity applications:
- **Primary Color:** Yellow (`#FFB81C`) for primary CTAs and highlights.
- **Background:** Warm Off-White (`#F5F2EA`) for a calm, sophisticated workspace.
- **Sidebar:** Charcoal (`#292827`) for strong navigation contrast.
- **Motion:** Fast micro-interactions (150ms) and smooth UI transitions (250-400ms) for a tactile feel.

## 🔒 Security & Architecture

- **Authoritative Backend:** All state changes and animations on the frontend strictly rely on secure Django POST operations. No "fake" frontend state.
- **Role-Based Access:** 
  - `_require_owner`: Ensures only the project creator can edit/delete project settings and tasks.
  - `_require_member`: Ensures only assigned team members can view the project contents and comment.

---
*Built as a showcase for clean architecture, efficient ORM usage, and premium UI design.*
