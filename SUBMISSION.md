# Final Submission Guide

Follow this guide to successfully submit your TaskFlow project.

### What to submit

1. **GitHub repository URL**, if the evaluator accepts GitHub.
2. **ZIP file** of the complete project, if file upload is required.

### Files that MUST be included

Ensure the root of your submission contains:
- `accounts/`
- `tasks/`
- `taskmanager/`
- `templates/`
- `migrations/` (inside apps)
- `static/` (if used)
- `manage.py`
- `requirements.txt`
- `README.md`
- `QUERIES.md`
- `SUBMISSION.md`
- `seed_demo.py`
- `docker-compose.yml` (if used)
- `.env.example`

### Files that MUST NOT be included

Double-check that you are **not** submitting:
- `.env` (Never commit real secrets)
- `venv/` (Virtual environments are generated locally)
- `__pycache__/`
- `*.pyc` or `*.pyo`
- Unnecessary IDE files (`.vscode/`, `.idea/`)
- Real secrets or passwords
- Local database files if not required

### Verification commands

Before zipping or pushing, run these locally to verify everything works:

```bash
python manage.py check
```

```bash
python manage.py test tasks --verbosity=2
```

```bash
python manage.py migrate
```

```bash
python manage.py runserver
```

### Demo accounts

The project comes with a seeder script (`python seed_demo.py`) that provisions the following accounts:

- **alice / password123** (Project Owner)
- **bob / password123** (Project Member)
- **admin / password123** (Administrator)

### Demo flow

Explain the recommended evaluator demonstration flow:

1. **Alice logs in**
2. → creates/opens a project
3. → creates a task
4. → assigns task to **Bob**
5. → **Bob logs in**
6. → Bob views the task
7. → Bob adds a comment
8. → Bob attempts unauthorized edit/delete
9. → Django strictly returns `403 Forbidden`
10. → **Admin** logs into the built-in Django Admin portal at `/admin/`
