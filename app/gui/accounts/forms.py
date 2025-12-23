from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password

from .models import CV, User, UserLLMConfig


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


class CVUploadForm(forms.ModelForm):
    """Form for CV file upload with validation."""

    ALLOWED_EXTENSIONS = ["pdf", "docx"]
    MAX_FILE_SIZE_MB = 10

    class Meta:
        model = CV
        fields = ["file"]
        widgets = {
            "file": forms.FileInput(attrs={"accept": ".pdf,.docx"}),
        }

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if not file:
            raise forms.ValidationError("Veuillez sélectionner un fichier.")

        # Check extension
        ext = file.name.split(".")[-1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise forms.ValidationError(f"Format non supporté. Formats acceptés : {', '.join(self.ALLOWED_EXTENSIONS)}")

        # Check file size
        max_size = self.MAX_FILE_SIZE_MB * 1024 * 1024
        if file.size > max_size:
            raise forms.ValidationError(f"Fichier trop volumineux. Taille max : {self.MAX_FILE_SIZE_MB} Mo")

        return file


class AccountIdentityForm(forms.ModelForm):
    """Form for updating user identity (name)."""

    class Meta:
        model = User
        fields = ["first_name", "last_name"]
        labels = {
            "first_name": "Prénom",
            "last_name": "Nom",
        }


class AccountEmailForm(forms.ModelForm):
    """Form for updating user email."""

    class Meta:
        model = User
        fields = ["email"]
        labels = {
            "email": "Adresse email",
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        return email


class AccountPasswordForm(forms.Form):
    """Form for changing password."""

    current_password = forms.CharField(
        label="Mot de passe actuel",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    new_password = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    confirm_password = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current = self.cleaned_data.get("current_password")
        if not self.user.check_password(current):
            raise forms.ValidationError("Mot de passe actuel incorrect.")
        return current

    def clean_new_password(self):
        password = self.cleaned_data.get("new_password")
        validate_password(password, self.user)
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm = cleaned_data.get("confirm_password")
        if new_password and confirm and new_password != confirm:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data["new_password"])
        self.user.save()
        return self.user


class UserLLMConfigForm(forms.ModelForm):
    """Form for custom LLM configuration."""

    class Meta:
        model = UserLLMConfig
        fields = ["is_enabled", "llm_endpoint", "llm_model", "llm_api_key"]
        labels = {
            "is_enabled": "Activer ma configuration LLM personnalisée",
            "llm_endpoint": "URL de l'endpoint LLM",
            "llm_model": "Nom du modèle",
            "llm_api_key": "Clé API",
        }
        widgets = {
            "llm_api_key": forms.PasswordInput(
                attrs={"class": "form-control", "placeholder": "Laisser vide pour conserver l'actuelle"}
            ),
            "llm_endpoint": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://api.openai.com/v1"}),
            "llm_model": forms.TextInput(attrs={"class": "form-control", "placeholder": "gpt-4o"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_enabled = cleaned_data.get("is_enabled")
        if is_enabled:
            if not cleaned_data.get("llm_endpoint"):
                raise forms.ValidationError("L'endpoint est requis si la configuration est activée.")
            if not cleaned_data.get("llm_model"):
                raise forms.ValidationError("Le modèle est requis si la configuration est activée.")
            # Allow empty API key if one already exists in database
            new_api_key = cleaned_data.get("llm_api_key")
            existing_api_key = self.instance.llm_api_key if self.instance else None
            if not new_api_key and not existing_api_key:
                raise forms.ValidationError("La clé API est requise si la configuration est activée.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # If API key field is empty, keep the existing one
        if not self.cleaned_data.get("llm_api_key") and self.instance.pk:
            instance.llm_api_key = UserLLMConfig.objects.get(pk=self.instance.pk).llm_api_key
        if commit:
            instance.save()
        return instance
