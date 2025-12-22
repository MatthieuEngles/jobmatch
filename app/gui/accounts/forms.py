from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["email", "username", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone",
            "availability",
            "salary_min",
            "salary_max",
            "remote_preference",
        ]
        widgets = {
            "availability": forms.Select(attrs={"class": "form-control"}),
            "remote_preference": forms.Select(attrs={"class": "form-control"}),
        }
