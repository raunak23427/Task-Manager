"""
Demo seed script — populates the database with realistic sample data:
  - 3 users (admin, raunak, daksh)
  - 2 projects
  - 8 tasks across statuses and priorities (some overdue)
  - Several comments

Run with: python seed_demo.py
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "taskmanager.settings")
django.setup()

from django.contrib.auth import get_user_model
from datetime import date, timedelta
from tasks.models import Project, Task, Comment, Status, Priority

User = get_user_model()

print("==> Creating users...")
admin, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@demo.com", "is_staff": True, "is_superuser": True})
admin.set_password("password123")
admin.save()

raunak, _ = User.objects.get_or_create(username="raunak", defaults={"email": "raunak@demo.com"})
raunak.set_password("password123")
raunak.save()

daksh, _ = User.objects.get_or_create(username="daksh", defaults={"email": "daksh@demo.com"})
daksh.set_password("password123")
daksh.save()

print("   Users: admin / raunak / daksh")

print("==> Creating projects...")
p1, _ = Project.objects.get_or_create(
    name="Website Redesign",
    defaults={
        "description": "Full redesign of the company website including new brand identity, improved UX, and mobile responsiveness.",
        "owner": admin,
    },
)

p2, _ = Project.objects.get_or_create(
    name="Mobile App MVP",
    defaults={
        "description": "Build the first version of the customer-facing mobile app for iOS and Android.",
        "owner": raunak,
    },
)

p3, _ = Project.objects.get_or_create(
    name="Q4 Marketing Campaign",
    defaults={
        "description": "Launch the new product features to our enterprise customers with targeted ads and email sequences.",
        "owner": daksh,
    },
)

p4, _ = Project.objects.get_or_create(
    name="Infrastructure Scaling",
    defaults={
        "description": "Migrate core databases to new clusters and upgrade message queues to handle increased load.",
        "owner": admin,
    },
)

print("==> Creating tasks...")
today = date.today()

tasks_data = [
    # Website Redesign tasks (Admin owned)
    dict(title="Design new homepage mockup",        status=Status.DONE,        priority=Priority.HIGH,   due_date=today - timedelta(days=10), project=p1, assigned_to=raunak),
    dict(title="Set up CI/CD pipeline",             status=Status.DONE,        priority=Priority.MEDIUM, due_date=today - timedelta(days=5),  project=p1, assigned_to=daksh),
    dict(title="Migrate blog to new CMS",           status=Status.IN_PROGRESS, priority=Priority.MEDIUM, due_date=today + timedelta(days=3),  project=p1, assigned_to=raunak),
    dict(title="Write SEO meta tags for all pages", status=Status.TODO,        priority=Priority.LOW,    due_date=today + timedelta(days=7),  project=p1, assigned_to=daksh),
    dict(title="Fix broken links audit",            status=Status.TODO,        priority=Priority.HIGH,   due_date=today - timedelta(days=2),  project=p1, assigned_to=admin),  # overdue!
    
    # Mobile App tasks (Raunak owned)
    dict(title="User authentication flow",          status=Status.DONE,        priority=Priority.HIGH,   due_date=today - timedelta(days=14), project=p2, assigned_to=daksh),
    dict(title="Push notification integration",     status=Status.IN_PROGRESS, priority=Priority.HIGH,   due_date=today - timedelta(days=1),  project=p2, assigned_to=raunak),  # overdue!
    dict(title="Offline mode support",              status=Status.TODO,        priority=Priority.MEDIUM, due_date=today + timedelta(days=10), project=p2, assigned_to=admin),
    dict(title="App Store submission checklist",    status=Status.TODO,        priority=Priority.LOW,    due_date=today + timedelta(days=14), project=p2, assigned_to=raunak),
    dict(title="Dark mode UI implementation",       status=Status.IN_PROGRESS, priority=Priority.MEDIUM, due_date=today + timedelta(days=5),  project=p2, assigned_to=daksh),
    dict(title="Analytics event tracking",          status=Status.TODO,        priority=Priority.LOW,    due_date=today + timedelta(days=8),  project=p2, assigned_to=daksh),

    # Marketing Campaign tasks (Daksh owned)
    dict(title="Draft email announcement sequence", status=Status.DONE,        priority=Priority.HIGH,   due_date=today - timedelta(days=3),  project=p3, assigned_to=raunak),
    dict(title="Design social media assets",        status=Status.IN_PROGRESS, priority=Priority.MEDIUM, due_date=today + timedelta(days=2),  project=p3, assigned_to=daksh),
    dict(title="Configure ad targeting parameters", status=Status.TODO,        priority=Priority.HIGH,   due_date=today + timedelta(days=4),  project=p3, assigned_to=admin),
    dict(title="Review campaign budget",            status=Status.IN_PROGRESS, priority=Priority.HIGH,   due_date=today - timedelta(days=2),  project=p3, assigned_to=daksh), # overdue!
    
    # Infrastructure tasks (Admin owned)
    dict(title="Audit current database IOPS",       status=Status.DONE,        priority=Priority.LOW,    due_date=today - timedelta(days=20), project=p4, assigned_to=admin),
    dict(title="Provision new staging clusters",    status=Status.IN_PROGRESS, priority=Priority.HIGH,   due_date=today + timedelta(days=1),  project=p4, assigned_to=admin),
    dict(title="Test failover mechanisms",          status=Status.TODO,        priority=Priority.HIGH,   due_date=today + timedelta(days=6),  project=p4, assigned_to=daksh),
    dict(title="Update disaster recovery docs",     status=Status.TODO,        priority=Priority.LOW,    due_date=today + timedelta(days=15), project=p4, assigned_to=raunak),
]

created_tasks = []
for td in tasks_data:
    t, created = Task.objects.get_or_create(title=td["title"], project=td["project"], defaults=td)
    if not created:
        for k, v in td.items():
            setattr(t, k, v)
        t.save()
    created_tasks.append(t)
    print(f"   {'[NEW]' if created else '[UPD]'} {t.title} [{t.get_status_display()}]")

print("==> Adding comments...")
comments = [
    (created_tasks[0], admin, "Looks great! Approved for development."),
    (created_tasks[0], raunak, "Thanks! I'll hand this off to the dev team now."),
    (created_tasks[1], daksh,   "Pipeline is green. All tests passing."),
    (created_tasks[2], raunak, "About 60% done. Hit a snag with image uploads."),
    (created_tasks[2], admin, "Let me know if you need help with the S3 config."),
    (created_tasks[4], admin, "Starting the audit now. Found ~15 broken links so far."),
    (created_tasks[5], daksh,   "Auth done — JWT + refresh tokens implemented."),
    (created_tasks[6], raunak, "Firebase SDK integrated, testing on iOS simulator."),
]

for task, author, body in comments:
    if not Comment.objects.filter(task=task, author=author, body=body).exists():
        Comment.objects.create(task=task, author=author, body=body)
        print(f"   Comment by {author.username} on '{task.title}'")

print("\n Demo data loaded!\n")
print("Login credentials:")
print("  admin / password123  (superuser, owns Website Redesign)")
print("  raunak / password123  (owns Mobile App MVP)")
print("  daksh   / password123  (regular user / member)")
print("\nGo to http://127.0.0.1:8000")
