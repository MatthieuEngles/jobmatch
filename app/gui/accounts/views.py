import logging

import requests
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.generic import CreateView

from .forms import (
    AccountEmailForm,
    AccountIdentityForm,
    AccountPasswordForm,
    CVUploadForm,
    UserLLMConfigForm,
    UserProfileForm,
    UserRegistrationForm,
)
from .models import CV, ExtractedLine, User, UserLLMConfig

logger = logging.getLogger(__name__)


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("home")


class UserRegistrationView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


@login_required
def profile_view(request):
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile")
    else:
        form = UserProfileForm(instance=request.user)

    # Get extracted lines grouped by content_type for career path display
    user = request.user
    experiences = user.extracted_lines.filter(content_type="experience", is_active=True).order_by(
        "order", "-created_at"
    )
    skills_hard = user.extracted_lines.filter(content_type="skill_hard", is_active=True).order_by(
        "order", "-created_at"
    )
    skills_soft = user.extracted_lines.filter(content_type="skill_soft", is_active=True).order_by(
        "order", "-created_at"
    )
    educations = user.extracted_lines.filter(content_type="education", is_active=True).order_by("order", "-created_at")
    certifications = user.extracted_lines.filter(content_type="certification", is_active=True).order_by(
        "order", "-created_at"
    )

    # Get user's CVs for documents section
    user_cvs = user.cvs.all()

    context = {
        "form": form,
        "experiences": experiences,
        "skills_hard": skills_hard,
        "skills_soft": skills_soft,
        "educations": educations,
        "certifications": certifications,
        "user_cvs": user_cvs,
    }
    return render(request, "accounts/profile.html", context)


@login_required
def delete_account_view(request):
    if request.method == "POST":
        request.user.delete()
        return redirect("home")
    return render(request, "accounts/delete_account.html")


@login_required
@require_POST
def cv_upload_view(request):
    """
    Handle CV upload and submit for async extraction via cv-ingestion microservice.
    Returns JSON response with task_id for polling.
    """
    form = CVUploadForm(request.POST, request.FILES)

    if not form.is_valid():
        return JsonResponse({"success": False, "error": form.errors.get("file", ["Erreur de validation"])[0]})

    uploaded_file = request.FILES["file"]

    # Create CV record with pending status
    cv = CV.objects.create(
        user=request.user,
        file=uploaded_file,
        original_filename=uploaded_file.name,
        extraction_status="processing",
    )

    try:
        # Call cv-ingestion async endpoint
        cv_ingestion_url = f"{settings.CV_INGESTION_URL}/extract/async"
        logger.info(f"Calling cv-ingestion async at {cv_ingestion_url}")

        # Reset file pointer and prepare request data
        cv.file.seek(0)
        files = {"file": (uploaded_file.name, cv.file.read(), uploaded_file.content_type)}

        # Include user's custom LLM config if enabled and user has premium+ subscription
        data = {}
        user = request.user
        if user.subscription_tier not in ("free", "basic"):
            try:
                llm_config = user.llm_config
                if llm_config.is_enabled and llm_config.llm_endpoint:
                    data["llm_endpoint"] = llm_config.llm_endpoint
                    data["llm_model"] = llm_config.llm_model
                    data["llm_api_key"] = llm_config.llm_api_key
                    logger.info(f"Using custom LLM config for user {user.id}")
            except UserLLMConfig.DoesNotExist:
                pass  # No custom config, use server defaults

        response = requests.post(
            cv_ingestion_url,
            files=files,
            data=data,
            timeout=30,  # Short timeout for async submission
        )

        if response.status_code != 200:
            raise requests.RequestException(f"cv-ingestion returned {response.status_code}")

        result = response.json()
        task_id = result.get("task_id")

        if not task_id:
            raise ValueError("No task_id returned from cv-ingestion")

        # Store task_id in CV for polling
        cv.task_id = task_id
        cv.save()

        logger.info(f"CV {cv.id} submitted for async extraction, task_id: {task_id}")

        return JsonResponse(
            {
                "success": True,
                "status": "processing",
                "task_id": task_id,
                "cv_id": cv.id,
                "message": "CV soumis pour extraction",
            }
        )

    except requests.Timeout:
        cv.extraction_status = "failed"
        cv.save()
        logger.error(f"CV {cv.id} submission timeout")
        return JsonResponse({"success": False, "error": "Timeout lors de la soumission. Réessayez plus tard."})

    except requests.RequestException as e:
        cv.extraction_status = "failed"
        cv.save()
        logger.error(f"CV {cv.id} submission failed: {e}")
        return JsonResponse({"success": False, "error": "Erreur de communication avec le service d'extraction."})

    except Exception as e:
        cv.extraction_status = "failed"
        cv.save()
        logger.error(f"CV {cv.id} submission error: {e}")
        return JsonResponse({"success": False, "error": f"Erreur lors de la soumission : {e}"})


@login_required
@require_GET
def cv_status_view(request, task_id):
    """
    Poll cv-ingestion for extraction status and process results when complete.
    """
    try:
        # Find CV by task_id
        cv = CV.objects.get(user=request.user, task_id=task_id)
    except CV.DoesNotExist:
        return JsonResponse({"success": False, "error": "CV non trouvé"}, status=404)

    # If already completed or failed, return stored status
    if cv.extraction_status == "completed":
        lines_count = cv.extracted_lines.count()
        return JsonResponse(
            {
                "success": True,
                "status": "completed",
                "message": f"Extraction terminée. {lines_count} éléments extraits.",
                "lines_count": lines_count,
            }
        )
    elif cv.extraction_status == "failed":
        return JsonResponse({"success": False, "status": "failed", "error": "L'extraction a échoué."})

    try:
        # Poll cv-ingestion for status
        status_url = f"{settings.CV_INGESTION_URL}/extract/status/{task_id}"
        response = requests.get(status_url, timeout=10)

        if response.status_code == 404:
            cv.extraction_status = "failed"
            cv.save()
            return JsonResponse({"success": False, "status": "failed", "error": "Tâche non trouvée."})

        if response.status_code != 200:
            return JsonResponse({"success": False, "error": f"Erreur du service d'extraction ({response.status_code})"})

        result = response.json()
        status = result.get("status")

        if status in ("pending", "processing"):
            return JsonResponse({"success": True, "status": status, "message": "Extraction en cours..."})

        elif status == "completed":
            # Process extracted lines
            extracted_lines = result.get("extracted_lines", [])
            lines_created = 0

            for idx, line_data in enumerate(extracted_lines):
                ExtractedLine.objects.create(
                    user=request.user,
                    source_cv=cv,
                    content_type=line_data.get("content_type", "other"),
                    content=line_data.get("content", ""),
                    order=line_data.get("order", idx),
                )
                lines_created += 1

            # Update CV status
            cv.extraction_status = "completed"
            cv.extracted_at = timezone.now()
            cv.save()

            logger.info(f"CV {cv.id} extraction completed: {lines_created} lines created")

            return JsonResponse(
                {
                    "success": True,
                    "status": "completed",
                    "message": f"CV importé avec succès. {lines_created} éléments extraits.",
                    "lines_count": lines_created,
                }
            )

        elif status == "failed":
            cv.extraction_status = "failed"
            cv.save()
            error_msg = result.get("error", "Erreur inconnue")
            logger.error(f"CV {cv.id} extraction failed: {error_msg}")
            return JsonResponse({"success": False, "status": "failed", "error": f"Extraction échouée: {error_msg}"})

        else:
            return JsonResponse({"success": False, "error": f"Status inconnu: {status}"})

    except requests.Timeout:
        return JsonResponse({"success": False, "error": "Timeout lors de la vérification du statut."})

    except requests.RequestException as e:
        logger.error(f"Status check failed for task {task_id}: {e}")
        return JsonResponse({"success": False, "error": "Erreur de communication avec le service."})

    except Exception as e:
        logger.error(f"Status check error for task {task_id}: {e}")
        return JsonResponse({"success": False, "error": f"Erreur: {e}"})


@login_required
@require_http_methods(["DELETE", "POST"])
def cv_delete_view(request, cv_id):
    """
    Delete a CV and its associated extracted lines.
    Accepts DELETE or POST (for form submissions).
    """
    try:
        cv = CV.objects.get(id=cv_id, user=request.user)
    except CV.DoesNotExist:
        return JsonResponse({"success": False, "error": "CV non trouvé"}, status=404)

    filename = cv.original_filename

    # Delete file from storage
    if cv.file:
        cv.file.delete(save=False)

    # Delete CV (cascades to ExtractedLines due to ForeignKey)
    cv.delete()

    logger.info(f"CV {cv_id} ({filename}) deleted by user {request.user.id}")

    return JsonResponse({"success": True, "message": f"CV '{filename}' supprimé avec succès."})


@login_required
@require_POST
def extracted_line_toggle_view(request, line_id):
    """
    Toggle the is_active status of an ExtractedLine.
    """
    try:
        line = ExtractedLine.objects.get(id=line_id, user=request.user)
    except ExtractedLine.DoesNotExist:
        return JsonResponse({"success": False, "error": "Élément non trouvé"}, status=404)

    line.toggle_active()
    logger.info(f"ExtractedLine {line_id} toggled to is_active={line.is_active} by user {request.user.id}")

    return JsonResponse(
        {
            "success": True,
            "is_active": line.is_active,
            "message": f"Élément {'activé' if line.is_active else 'désactivé'}.",
        }
    )


@login_required
def account_settings_view(request):
    """
    Account settings page with multiple sections:
    - Identity (name)
    - Email
    - Password
    - Subscription
    - LLM Configuration
    - Data export (RGPD)
    - Account deletion
    """
    user = request.user

    # Get or create LLM config
    llm_config, _ = UserLLMConfig.objects.get_or_create(user=user)

    # Initialize forms
    identity_form = AccountIdentityForm(instance=user)
    email_form = AccountEmailForm(instance=user)
    password_form = AccountPasswordForm(user)
    llm_form = UserLLMConfigForm(instance=llm_config)

    # Track which form was submitted and any messages
    success_message = None
    error_message = None

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "identity":
            identity_form = AccountIdentityForm(request.POST, instance=user)
            if identity_form.is_valid():
                identity_form.save()
                success_message = "Identité mise à jour avec succès."
            else:
                error_message = "Erreur lors de la mise à jour de l'identité."

        elif form_type == "email":
            email_form = AccountEmailForm(request.POST, instance=user)
            if email_form.is_valid():
                email_form.save()
                success_message = "Email mis à jour avec succès."
            else:
                error_message = "Erreur lors de la mise à jour de l'email."

        elif form_type == "password":
            password_form = AccountPasswordForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                # Re-authenticate to prevent logout
                login(request, user)
                success_message = "Mot de passe changé avec succès."
            else:
                error_message = "Erreur lors du changement de mot de passe."

        elif form_type == "llm":
            llm_form = UserLLMConfigForm(request.POST, instance=llm_config)
            if llm_form.is_valid():
                llm_form.save()
                success_message = "Configuration LLM mise à jour avec succès."
            else:
                # Show specific validation errors
                if llm_form.non_field_errors():
                    error_message = llm_form.non_field_errors()[0]
                else:
                    error_message = "Erreur lors de la mise à jour de la configuration LLM."

        elif form_type == "subscription":
            new_tier = request.POST.get("subscription_tier")
            valid_tiers = ["free", "basic", "premium", "headhunter", "enterprise"]
            if new_tier in valid_tiers:
                user.subscription_tier = new_tier
                user.save(update_fields=["subscription_tier"])
                success_message = f"Abonnement mis à jour : {user.get_subscription_tier_display()}"
            else:
                error_message = "Plan d'abonnement invalide."

    context = {
        "identity_form": identity_form,
        "email_form": email_form,
        "password_form": password_form,
        "llm_form": llm_form,
        "success_message": success_message,
        "error_message": error_message,
    }

    return render(request, "accounts/settings.html", context)


@login_required
def export_data_view(request):
    """
    Export all user data as JSON file (RGPD compliance).
    """
    import json

    from django.http import HttpResponse

    user = request.user

    # Collect all user data
    user_data = {
        "profile": {
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "subscription_tier": user.subscription_tier,
            "availability": user.availability,
            "salary_min": user.salary_min,
            "salary_max": user.salary_max,
            "remote_preference": user.remote_preference,
            "is_job_seeker": user.is_job_seeker,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "cvs": [],
        "extracted_lines": [],
        "cover_letters": [],
    }

    # Export CVs
    for cv in user.cvs.all():
        user_data["cvs"].append(
            {
                "id": cv.id,
                "filename": cv.original_filename,
                "uploaded_at": cv.uploaded_at.isoformat() if cv.uploaded_at else None,
                "extraction_status": cv.extraction_status,
                "extracted_at": cv.extracted_at.isoformat() if cv.extracted_at else None,
            }
        )

    # Export extracted lines
    for line in user.extracted_lines.all():
        user_data["extracted_lines"].append(
            {
                "id": line.id,
                "content_type": line.content_type,
                "content": line.content,
                "is_active": line.is_active,
                "order": line.order,
                "source_cv_id": line.source_cv_id,
                "created_at": line.created_at.isoformat() if line.created_at else None,
                "modified_at": line.modified_at.isoformat() if line.modified_at else None,
            }
        )

    # Export cover letters
    for letter in user.cover_letters.all():
        user_data["cover_letters"].append(
            {
                "id": letter.id,
                "title": letter.title,
                "filename": letter.original_filename,
                "uploaded_at": letter.uploaded_at.isoformat() if letter.uploaded_at else None,
            }
        )

    # Export LLM config if exists
    try:
        llm_config = user.llm_config
        user_data["llm_config"] = {
            "is_enabled": llm_config.is_enabled,
            "llm_endpoint": llm_config.llm_endpoint,
            "llm_model": llm_config.llm_model,
            # Note: API key not exported for security
        }
    except UserLLMConfig.DoesNotExist:
        user_data["llm_config"] = None

    # Create JSON response
    response = HttpResponse(
        json.dumps(user_data, indent=2, ensure_ascii=False),
        content_type="application/json",
    )
    response["Content-Disposition"] = f'attachment; filename="jobmatch_data_{user.id}.json"'

    logger.info(f"User {user.id} exported their data")

    return response


def pricing_view(request):
    """Display the pricing page with plan comparison."""
    return render(request, "accounts/pricing.html")
