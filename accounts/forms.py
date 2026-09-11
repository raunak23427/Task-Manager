from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()

_attrs = {"class": "form-input"}


class RegisterForm(UserCreationForm):
    """Registration form with styled widgets."""

    class Meta:
        model  = User
        fields = ("username", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={**_attrs, "placeholder": "Choose a username"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Style password fields
        self.fields["password1"].widget = forms.PasswordInput(attrs={**_attrs, "placeholder": "Choose a password"})
        self.fields["password2"].widget = forms.PasswordInput(attrs={**_attrs, "placeholder": "Confirm password"})
        # Remove the verbose help text for password fields to keep UI clean
        self.fields["password1"].help_text = None
        self.fields["password2"].help_text = None
