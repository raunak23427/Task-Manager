from django import forms
from django.contrib.auth import get_user_model

from .models import Project, Task, Comment

User = get_user_model()

_input_attrs  = {"class": "form-input"}
_select_attrs = {"class": "form-input"}
_textarea_attrs = {"class": "form-input"}


class ProjectForm(forms.ModelForm):
    class Meta:
        model   = Project
        fields  = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={**_input_attrs, "placeholder": "e.g. Website Redesign"}),
            "description": forms.Textarea(attrs={**_textarea_attrs, "rows": 4, "placeholder": "What is this project about?"}),
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model   = Task
        fields  = ["title", "status", "priority", "due_date", "assigned_to"]
        widgets = {
            "title":    forms.TextInput(attrs={**_input_attrs, "placeholder": "Describe the task clearly"}),
            "status":   forms.Select(attrs=_select_attrs),
            "priority": forms.Select(attrs=_select_attrs),
            "due_date": forms.DateInput(attrs={**_input_attrs, "type": "date"}),
            "assigned_to": forms.Select(attrs=_select_attrs),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset  = User.objects.all().order_by("username")
        self.fields["assigned_to"].empty_label = "— Unassigned —"


class CommentForm(forms.ModelForm):
    class Meta:
        model   = Comment
        fields  = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={
                **_textarea_attrs,
                "rows": 3,
                "placeholder": "Write a comment…",
            }),
        }
        labels = {"body": ""}
