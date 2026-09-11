from django import forms
from django.contrib.auth import get_user_model

from .models import Project, Task, Comment

User = get_user_model()


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "status", "priority", "due_date", "assigned_to"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show all users as potential assignees (keeps it simple)
        self.fields["assigned_to"].queryset = User.objects.all().order_by("username")
        self.fields["assigned_to"].empty_label = "— Unassigned —"


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 3, "placeholder": "Add a comment…"}),
        }
        labels = {"body": ""}
