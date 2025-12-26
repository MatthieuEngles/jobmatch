import contextlib
import json as json_module
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
from .models import (
    APPLICATION_STATUS_CHOICES,
    CV,
    SOCIAL_LINK_TYPE_CHOICES,
    Application,
    CandidateProfile,
    ChatConversation,
    ChatMessage,
    DocxTemplate,
    ExtractedLine,
    Pitch,
    ProfessionalSuccess,
    ProfileItemSelection,
    SocialLink,
    User,
    UserLLMConfig,
)

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

    user = request.user

    # Get or create default "Complet" profile
    default_profile, _ = CandidateProfile.get_or_create_default(user)

    # Get current profile from session or use default
    current_profile_id = request.session.get("current_profile_id")
    if current_profile_id:
        try:
            current_profile = CandidateProfile.objects.get(id=current_profile_id, user=user)
        except CandidateProfile.DoesNotExist:
            current_profile = default_profile
            request.session["current_profile_id"] = default_profile.id
    else:
        current_profile = user.candidate_profiles.filter(is_default=True).first() or default_profile
        request.session["current_profile_id"] = current_profile.id

    # Get all user profiles for dropdown
    candidate_profiles = user.candidate_profiles.all()

    # Get extracted lines grouped by content_type for career path display
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
    languages = user.extracted_lines.filter(content_type="language", is_active=True).order_by("order", "-created_at")
    interests = user.extracted_lines.filter(content_type="interest", is_active=True).order_by("order", "-created_at")

    # Build selection map for current profile
    profile_selections = {}
    for selection in current_profile.item_selections.all():
        profile_selections[selection.extracted_line_id] = selection.is_selected

    # Get user's CVs for documents section
    user_cvs = user.cvs.all()

    # Get user's social links
    social_links = user.social_links.all()

    context = {
        "form": form,
        "experiences": experiences,
        "skills_hard": skills_hard,
        "skills_soft": skills_soft,
        "educations": educations,
        "certifications": certifications,
        "languages": languages,
        "interests": interests,
        "user_cvs": user_cvs,
        "candidate_profiles": candidate_profiles,
        "current_profile": current_profile,
        "profile_selections": profile_selections,
        "social_links": social_links,
        "social_link_types": SOCIAL_LINK_TYPE_CHOICES,
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
def photo_upload_view(request):
    """Handle profile photo upload with preview and cropping."""
    if "photo" not in request.FILES:
        return JsonResponse({"success": False, "error": "Aucune photo fournie"}, status=400)

    photo = request.FILES["photo"]

    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if photo.content_type not in allowed_types:
        return JsonResponse(
            {"success": False, "error": "Format non supporte. Utilisez JPG, PNG ou WebP."},
            status=400,
        )

    # Validate file size (max 5MB)
    max_size = 5 * 1024 * 1024
    if photo.size > max_size:
        return JsonResponse(
            {"success": False, "error": "La photo ne doit pas depasser 5 Mo"},
            status=400,
        )

    # Delete old photo if exists
    if request.user.photo:
        request.user.photo.delete(save=False)

    # Save new photo
    request.user.photo = photo
    request.user.save(update_fields=["photo"])

    logger.info(f"User {request.user.id} uploaded a new profile photo")

    return JsonResponse(
        {
            "success": True,
            "photo_url": request.user.photo.url,
            "message": "Photo mise a jour",
        }
    )


@login_required
@require_POST
def photo_delete_view(request):
    """Delete the user's profile photo."""
    if request.user.photo:
        request.user.photo.delete(save=False)
        request.user.photo = None
        request.user.save(update_fields=["photo"])
        logger.info(f"User {request.user.id} deleted their profile photo")

    return JsonResponse({"success": True, "message": "Photo supprimee"})


@login_required
@require_POST
def social_link_add_view(request):
    """Add a new social link."""
    import json

    try:
        data = json.loads(request.body)
        link_type = data.get("link_type")
        url = data.get("url")

        if not link_type or not url:
            return JsonResponse(
                {"success": False, "error": "Type et URL requis"},
                status=400,
            )

        # Validate link type
        valid_types = [t[0] for t in SOCIAL_LINK_TYPE_CHOICES]
        if link_type not in valid_types:
            return JsonResponse(
                {"success": False, "error": "Type de lien invalide"},
                status=400,
            )

        # Create the link
        link = SocialLink.objects.create(
            user=request.user,
            link_type=link_type,
            url=url,
            order=request.user.social_links.count(),
        )

        return JsonResponse(
            {
                "success": True,
                "link": {
                    "id": link.id,
                    "link_type": link.link_type,
                    "link_type_display": link.get_link_type_display(),
                    "url": link.url,
                },
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Donnees invalides"},
            status=400,
        )


@login_required
@require_POST
def social_link_delete_view(request, link_id):
    """Delete a social link."""
    try:
        link = SocialLink.objects.get(id=link_id, user=request.user)
        link.delete()
        return JsonResponse({"success": True})
    except SocialLink.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Lien non trouve"},
            status=404,
        )


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
                # Build line data with optional structured fields
                line_kwargs = {
                    "user": request.user,
                    "source_cv": cv,
                    "content_type": line_data.get("content_type", "other"),
                    "content": line_data.get("content", ""),
                    "order": line_data.get("order", idx),
                }

                # Add structured fields for experience/education if present
                if line_data.get("entity"):
                    line_kwargs["entity"] = line_data["entity"]
                if line_data.get("dates"):
                    line_kwargs["dates"] = line_data["dates"]
                if line_data.get("position"):
                    line_kwargs["position"] = line_data["position"]
                if line_data.get("description"):
                    line_kwargs["description"] = line_data["description"]

                # Add structured fields for personal_info
                if line_data.get("first_name"):
                    line_kwargs["first_name"] = line_data["first_name"]
                if line_data.get("last_name"):
                    line_kwargs["last_name"] = line_data["last_name"]
                if line_data.get("email"):
                    line_kwargs["email"] = line_data["email"]
                if line_data.get("phone"):
                    line_kwargs["phone"] = line_data["phone"]
                if line_data.get("location"):
                    line_kwargs["location"] = line_data["location"]

                # Add structured fields for social_link
                if line_data.get("link_type"):
                    line_kwargs["link_type"] = line_data["link_type"]
                if line_data.get("url"):
                    line_kwargs["url"] = line_data["url"]

                ExtractedLine.objects.create(**line_kwargs)
                lines_created += 1

                # Sync personal_info to User model (only if fields are empty)
                content_type = line_data.get("content_type")
                if content_type == "personal_info":
                    user = request.user
                    updated = False
                    if line_data.get("first_name") and not user.first_name:
                        user.first_name = line_data["first_name"]
                        updated = True
                    if line_data.get("last_name") and not user.last_name:
                        user.last_name = line_data["last_name"]
                        updated = True
                    if line_data.get("phone") and not user.phone:
                        user.phone = line_data["phone"]
                        updated = True
                    if line_data.get("location") and not user.location:
                        user.location = line_data["location"]
                        updated = True
                    if updated:
                        user.save()
                        logger.info(f"User {user.id} personal info updated from CV extraction")

                # Create SocialLink from extracted social_link data
                elif content_type == "social_link" and line_data.get("url"):
                    link_type = line_data.get("link_type", "other")
                    url = line_data["url"]
                    # Avoid duplicates: check if this URL already exists for the user
                    if not SocialLink.objects.filter(user=request.user, url=url).exists():
                        SocialLink.objects.create(
                            user=request.user,
                            link_type=link_type,
                            url=url,
                            order=line_data.get("order", idx),
                        )
                        logger.info(f"SocialLink created for user {request.user.id}: {link_type} - {url}")

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

        elif form_type == "ai_preferences":
            try:
                autonomy_level = int(request.POST.get("ai_autonomy_level", 3))
                if 1 <= autonomy_level <= 5:
                    user.ai_autonomy_level = autonomy_level
                    user.save(update_fields=["ai_autonomy_level"])
                    success_message = "Préférences IA mises à jour avec succès."
                else:
                    error_message = "Niveau d'autonomie invalide (doit être entre 1 et 5)."
            except (ValueError, TypeError):
                error_message = "Niveau d'autonomie invalide."

        elif form_type == "docx_template":
            try:
                template_id = int(request.POST.get("docx_template_id", 0))
                if template_id:
                    template = DocxTemplate.objects.filter(id=template_id).first()
                    if template:
                        user.docx_template = template
                        user.save(update_fields=["docx_template"])
                        success_message = f"Template '{template.name}' sélectionné."
                    else:
                        error_message = "Template introuvable."
                else:
                    error_message = "Veuillez sélectionner un template."
            except (ValueError, TypeError):
                error_message = "Template invalide."

    # Get all available DOCX templates
    docx_templates = DocxTemplate.objects.all()

    context = {
        "identity_form": identity_form,
        "email_form": email_form,
        "password_form": password_form,
        "llm_form": llm_form,
        "docx_templates": docx_templates,
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


# ============================================================================
# Candidate Profile Management Views
# ============================================================================


@login_required
@require_POST
def profile_switch_view(request):
    """Switch to a different candidate profile."""
    import json

    try:
        data = json.loads(request.body)
        profile_id = data.get("profile_id")
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

    try:
        profile = CandidateProfile.objects.get(id=profile_id, user=request.user)
    except CandidateProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "Profil non trouvé"}, status=404)

    # Store in session
    request.session["current_profile_id"] = profile.id

    logger.info(f"User {request.user.id} switched to profile '{profile.title}'")

    return JsonResponse(
        {
            "success": True,
            "profile_id": profile.id,
            "profile_title": profile.title,
            "message": f"Profil '{profile.title}' sélectionné",
        }
    )


@login_required
@require_POST
def profile_create_view(request):
    """Create a new candidate profile."""
    import json

    try:
        data = json.loads(request.body)
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

    if not title:
        return JsonResponse({"success": False, "error": "Le titre est requis"}, status=400)

    # Check if title already exists for this user
    if CandidateProfile.objects.filter(user=request.user, title=title).exists():
        return JsonResponse({"success": False, "error": "Un profil avec ce titre existe déjà"}, status=400)

    # Create profile
    profile = CandidateProfile.objects.create(
        user=request.user,
        title=title,
        description=description,
    )

    # Initialize with all items selected (copy from "Complet" or all active lines)
    profile.initialize_all_selected()

    # Switch to new profile
    request.session["current_profile_id"] = profile.id

    logger.info(f"User {request.user.id} created profile '{profile.title}'")

    return JsonResponse(
        {
            "success": True,
            "profile_id": profile.id,
            "profile_title": profile.title,
            "message": f"Profil '{profile.title}' créé",
        }
    )


@login_required
@require_POST
def profile_update_view(request, profile_id):
    """Update an existing candidate profile."""
    import json

    try:
        profile = CandidateProfile.objects.get(id=profile_id, user=request.user)
    except CandidateProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "Profil non trouvé"}, status=404)

    try:
        data = json.loads(request.body)
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

    if not title:
        return JsonResponse({"success": False, "error": "Le titre est requis"}, status=400)

    # Check if title already exists for another profile
    if CandidateProfile.objects.filter(user=request.user, title=title).exclude(id=profile_id).exists():
        return JsonResponse({"success": False, "error": "Un profil avec ce titre existe déjà"}, status=400)

    # Prevent renaming "Complet" profile
    if profile.title == "Complet" and title != "Complet":
        return JsonResponse({"success": False, "error": "Le profil 'Complet' ne peut pas être renommé"}, status=400)

    profile.title = title
    profile.description = description
    profile.save()

    logger.info(f"User {request.user.id} updated profile '{profile.title}'")

    return JsonResponse(
        {
            "success": True,
            "profile_id": profile.id,
            "profile_title": profile.title,
            "message": f"Profil '{profile.title}' mis à jour",
        }
    )


@login_required
@require_http_methods(["DELETE", "POST"])
def profile_delete_view(request, profile_id):
    """Delete a candidate profile."""
    try:
        profile = CandidateProfile.objects.get(id=profile_id, user=request.user)
    except CandidateProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "Profil non trouvé"}, status=404)

    # Prevent deleting "Complet" profile
    if profile.title == "Complet":
        return JsonResponse({"success": False, "error": "Le profil 'Complet' ne peut pas être supprimé"}, status=400)

    title = profile.title
    profile.delete()

    # If deleted profile was current, switch to default
    if request.session.get("current_profile_id") == profile_id:
        default_profile = request.user.candidate_profiles.filter(is_default=True).first()
        if default_profile:
            request.session["current_profile_id"] = default_profile.id

    logger.info(f"User {request.user.id} deleted profile '{title}'")

    return JsonResponse(
        {
            "success": True,
            "message": f"Profil '{title}' supprimé",
        }
    )


@login_required
@require_POST
def profile_item_toggle_view(request, profile_id, line_id):
    """Toggle selection status of an item in a profile."""
    try:
        profile = CandidateProfile.objects.get(id=profile_id, user=request.user)
    except CandidateProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "Profil non trouvé"}, status=404)

    try:
        line = ExtractedLine.objects.get(id=line_id, user=request.user)
    except ExtractedLine.DoesNotExist:
        return JsonResponse({"success": False, "error": "Élément non trouvé"}, status=404)

    # Get or create selection, then toggle
    selection, created = ProfileItemSelection.objects.get_or_create(
        profile=profile,
        extracted_line=line,
        defaults={"is_selected": False},  # If creating, set to False (was True by default, now toggled)
    )

    if not created:
        selection.is_selected = not selection.is_selected
        selection.save()

    logger.info(
        f"User {request.user.id} toggled item {line_id} to {selection.is_selected} in profile '{profile.title}'"
    )

    return JsonResponse(
        {
            "success": True,
            "is_selected": selection.is_selected,
            "message": f"Élément {'sélectionné' if selection.is_selected else 'désélectionné'}",
        }
    )


@login_required
@require_GET
def profile_selections_view(request, profile_id):
    """Get all selections for a profile (used when switching profiles)."""
    try:
        profile = CandidateProfile.objects.get(id=profile_id, user=request.user)
    except CandidateProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "Profil non trouvé"}, status=404)

    # Build selection map
    selections = {}
    for selection in profile.item_selections.all():
        selections[selection.extracted_line_id] = selection.is_selected

    # For items without explicit selection, they are selected by default
    all_line_ids = list(ExtractedLine.objects.filter(user=request.user, is_active=True).values_list("id", flat=True))

    result = {}
    for line_id in all_line_ids:
        result[line_id] = selections.get(line_id, True)  # Default to True if not set

    return JsonResponse(
        {
            "success": True,
            "profile_id": profile.id,
            "profile_title": profile.title,
            "selections": result,
        }
    )


# ============================================================================
# Chat AI Assistant Views (STAR Coaching)
# ============================================================================


def _build_user_context(user, coaching_type: str = "star") -> dict:
    """Build user context dict for AI assistant.

    Args:
        user: The Django user object.
        coaching_type: Type of coaching ('star' or 'pitch').
            For 'pitch', includes full STAR data of successes.
    """
    # Get current profile title
    profile_title = ""
    default_profile = user.candidate_profiles.filter(is_default=True).first()
    if default_profile:
        profile_title = default_profile.title

    # Get experiences
    experiences = []
    for exp in user.extracted_lines.filter(content_type="experience", is_active=True)[:5]:
        experiences.append(
            {
                "entity": exp.entity or "",
                "position": exp.position or "",
                "dates": exp.dates or "",
                "description": exp.description or "",
            }
        )

    # Get education (for pitch coaching)
    education = []
    for edu in user.extracted_lines.filter(content_type="education", is_active=True)[:3]:
        education.append(
            {
                "entity": edu.entity or "",
                "degree": edu.position or "",  # position stores diploma name for education
                "dates": edu.dates or "",
            }
        )

    # Get skills (both hard and soft, for pitch coaching)
    skills = [
        line.content
        for line in user.extracted_lines.filter(content_type__in=["skill_hard", "skill_soft"], is_active=True)[:10]
    ]

    # Get interests
    interests = [line.content for line in user.extracted_lines.filter(content_type="interest", is_active=True)[:5]]

    # Get existing successes
    # For pitch coaching, include full STAR data to help build the pitch
    if coaching_type == "pitch":
        existing_successes = []
        for s in user.professional_successes.filter(is_draft=False)[:5]:
            existing_successes.append(
                {
                    "title": s.title,
                    "situation": s.situation,
                    "task": s.task,
                    "action": s.action,
                    "result": s.result,
                    "skills_demonstrated": s.skills_demonstrated,
                    "is_complete": s.is_complete(),
                }
            )
        # Also include drafts if we don't have enough finalized successes
        if len(existing_successes) < 3:
            for s in user.professional_successes.filter(is_draft=True)[: 3 - len(existing_successes)]:
                existing_successes.append(
                    {
                        "title": s.title,
                        "situation": s.situation,
                        "task": s.task,
                        "action": s.action,
                        "result": s.result,
                        "skills_demonstrated": s.skills_demonstrated,
                        "is_complete": s.is_complete(),
                    }
                )
    else:
        # For STAR coaching, just include titles to avoid repetition
        existing_successes = [
            {"title": s.title, "is_complete": s.is_complete()} for s in user.professional_successes.all()[:3]
        ]

    return {
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "location": user.location or "",
        "profile_title": profile_title,
        "experiences": experiences,
        "education": education,
        "skills": skills,
        "interests": interests,
        "existing_successes": existing_successes,
        "autonomy_level": user.ai_autonomy_level,
    }


def _get_user_llm_config(user) -> dict | None:
    """Get user's custom LLM config if they are Premium+ and have it enabled.

    Returns dict with llm_endpoint, llm_model, llm_api_key or None.
    """
    if user.subscription_tier in ("free", "basic"):
        return None
    try:
        llm_config = user.llm_config
        if llm_config.is_enabled and llm_config.llm_endpoint:
            return {
                "llm_endpoint": llm_config.llm_endpoint,
                "llm_model": llm_config.llm_model,
                "llm_api_key": llm_config.llm_api_key,
            }
    except UserLLMConfig.DoesNotExist:
        pass
    return None


@login_required
@require_POST
def chat_start_view(request):
    """Start a new chat conversation for STAR or Pitch coaching."""
    import json

    user = request.user

    # Get coaching type from request (default to STAR)
    try:
        data = json.loads(request.body) if request.body else {}
        coaching_type = data.get("coaching_type", "star")
    except json.JSONDecodeError:
        coaching_type = "star"

    # Validate coaching type
    if coaching_type not in ("star", "pitch"):
        coaching_type = "star"

    # Create conversation in DB
    context_snapshot = _build_user_context(user, coaching_type=coaching_type)
    conversation = ChatConversation.objects.create(
        user=user,
        coaching_type=coaching_type,
        context_snapshot=context_snapshot,
    )

    try:
        # Call ai-assistant to start conversation
        ai_url = f"{settings.AI_ASSISTANT_URL}/chat/start"
        payload = {
            "conversation_id": conversation.id,
            "user_context": context_snapshot,
            "coaching_type": coaching_type,
        }

        # Add user's custom LLM config if Premium+
        llm_config = _get_user_llm_config(user)
        if llm_config:
            payload["llm_config"] = llm_config
            logger.info(f"Using custom LLM config for user {user.id} in chat")

        response = requests.post(ai_url, json=payload, timeout=30)

        if response.status_code != 200:
            raise requests.RequestException(f"ai-assistant returned {response.status_code}")

        result = response.json()
        task_id = result.get("task_id")

        if not task_id:
            raise ValueError("No task_id returned from ai-assistant")

        # Create a pending ChatMessage for the assistant's initial response
        ChatMessage.objects.create(
            conversation=conversation,
            role="assistant",
            content="",  # Will be filled when polling completes
            status="pending",
            task_id=task_id,
        )

        logger.info(f"Chat conversation {conversation.id} started, task_id: {task_id}")

        return JsonResponse(
            {
                "success": True,
                "conversation_id": conversation.id,
                "task_id": task_id,
            }
        )

    except requests.Timeout:
        conversation.status = "abandoned"
        conversation.save()
        return JsonResponse({"success": False, "error": "Timeout lors du démarrage du chat."})

    except requests.RequestException as e:
        conversation.status = "abandoned"
        conversation.save()
        logger.error(f"Chat start failed: {e}")
        return JsonResponse({"success": False, "error": "Erreur de communication avec l'assistant IA."})

    except Exception as e:
        conversation.status = "abandoned"
        conversation.save()
        logger.error(f"Chat start error: {e}")
        return JsonResponse({"success": False, "error": f"Erreur: {e}"})


@login_required
@require_POST
def chat_message_view(request):
    """Send a message in a chat conversation."""
    import json

    try:
        data = json.loads(request.body)
        conversation_id = data.get("conversation_id")
        message_content = data.get("message", "").strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"success": False, "error": "Données invalides"}, status=400)

    if not message_content:
        return JsonResponse({"success": False, "error": "Message vide"}, status=400)

    # Get conversation
    try:
        conversation = ChatConversation.objects.get(id=conversation_id, user=request.user)
    except ChatConversation.DoesNotExist:
        return JsonResponse({"success": False, "error": "Conversation non trouvée"}, status=404)

    # Save user message
    user_msg = conversation.add_user_message(message_content)

    # Build history for AI
    history = []
    for msg in conversation.get_messages():
        if msg.id != user_msg.id:  # Exclude the just-added message
            history.append({"role": msg.role, "content": msg.content})

    # Build user context with conversation's coaching type
    coaching_type = conversation.coaching_type or "star"
    user_context = _build_user_context(request.user, coaching_type=coaching_type)

    try:
        # Call ai-assistant async endpoint
        ai_url = f"{settings.AI_ASSISTANT_URL}/chat/message/async"
        payload = {
            "conversation_id": conversation.id,
            "message": message_content,
            "history": history,
            "user_context": user_context,
            "coaching_type": coaching_type,
        }

        # Add user's custom LLM config if Premium+
        llm_config = _get_user_llm_config(request.user)
        if llm_config:
            payload["llm_config"] = llm_config

        response = requests.post(ai_url, json=payload, timeout=30)

        if response.status_code != 200:
            raise requests.RequestException(f"ai-assistant returned {response.status_code}")

        result = response.json()
        task_id = result.get("task_id")

        if not task_id:
            raise ValueError("No task_id returned from ai-assistant")

        # Create pending assistant message
        assistant_msg = ChatMessage.objects.create(
            conversation=conversation,
            role="assistant",
            content="",
            status="processing",
            task_id=task_id,
        )

        logger.info(f"Chat message sent for conversation {conversation_id}, task_id: {task_id}")

        return JsonResponse(
            {
                "success": True,
                "task_id": task_id,
                "message_id": assistant_msg.id,
            }
        )

    except requests.Timeout:
        return JsonResponse({"success": False, "error": "Timeout lors de l'envoi du message."})

    except requests.RequestException as e:
        logger.error(f"Chat message failed: {e}")
        return JsonResponse({"success": False, "error": "Erreur de communication avec l'assistant IA."})

    except Exception as e:
        logger.error(f"Chat message error: {e}")
        return JsonResponse({"success": False, "error": f"Erreur: {e}"})


@login_required
@require_GET
def chat_status_view(request, task_id):
    """Poll for chat message status."""
    # Find the message by task_id
    try:
        message = ChatMessage.objects.get(
            task_id=task_id,
            conversation__user=request.user,
        )
    except ChatMessage.DoesNotExist:
        return JsonResponse({"success": False, "error": "Message non trouvé"}, status=404)

    # If already completed, return stored content
    if message.status == "completed":
        return JsonResponse(
            {
                "success": True,
                "status": "completed",
                "response": message.content,
                "extracted_data": message.extracted_data,
            }
        )
    elif message.status == "failed":
        return JsonResponse(
            {
                "success": False,
                "status": "failed",
                "error": "La génération a échoué.",
            }
        )

    try:
        # Poll ai-assistant for status
        status_url = f"{settings.AI_ASSISTANT_URL}/chat/message/status/{task_id}"
        response = requests.get(status_url, timeout=10)

        if response.status_code == 404:
            message.status = "failed"
            message.save()
            return JsonResponse({"success": False, "status": "failed", "error": "Tâche non trouvée."})

        if response.status_code != 200:
            return JsonResponse({"success": False, "error": f"Erreur du service ({response.status_code})"})

        result = response.json()
        status = result.get("status")

        if status in ("pending", "processing"):
            return JsonResponse({"success": True, "status": status})

        elif status == "completed":
            response_text = result.get("response", "")
            extracted_data = result.get("extracted_data") or {}

            # Update message
            message.content = response_text
            message.status = "completed"
            message.extracted_data = extracted_data
            message.save()

            logger.info(f"Chat response received for task {task_id}")

            return JsonResponse(
                {
                    "success": True,
                    "status": "completed",
                    "response": response_text,
                    "extracted_data": extracted_data,
                }
            )

        elif status == "failed":
            error_msg = result.get("error", "Erreur inconnue")
            message.status = "failed"
            message.save()
            return JsonResponse({"success": False, "status": "failed", "error": error_msg})

        else:
            return JsonResponse({"success": False, "error": f"Status inconnu: {status}"})

    except requests.Timeout:
        return JsonResponse({"success": False, "error": "Timeout lors de la vérification."})

    except requests.RequestException as e:
        logger.error(f"Chat status check failed: {e}")
        return JsonResponse({"success": False, "error": "Erreur de communication."})


@login_required
@require_GET
def chat_history_view(request, conversation_id):
    """Get chat conversation history."""
    try:
        conversation = ChatConversation.objects.get(id=conversation_id, user=request.user)
    except ChatConversation.DoesNotExist:
        return JsonResponse({"success": False, "error": "Conversation non trouvée"}, status=404)

    messages = []
    for msg in conversation.get_messages():
        messages.append(
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "status": msg.status,
                "task_id": msg.task_id,
                "created_at": msg.created_at.isoformat(),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "conversation_id": conversation.id,
            "status": conversation.status,
            "messages": messages,
        }
    )


@login_required
@require_POST
def chat_start_stream_view(request):
    """Start a new chat conversation with streaming response.

    Proxies SSE stream from ai-assistant to the frontend.
    """
    import json

    from django.http import StreamingHttpResponse

    user = request.user

    # Get coaching type from request (default to STAR)
    try:
        data = json.loads(request.body) if request.body else {}
        coaching_type = data.get("coaching_type", "star")
    except json.JSONDecodeError:
        coaching_type = "star"

    # Validate coaching type
    if coaching_type not in ("star", "pitch"):
        coaching_type = "star"

    # Create conversation in DB
    context_snapshot = _build_user_context(user, coaching_type=coaching_type)
    conversation = ChatConversation.objects.create(
        user=user,
        coaching_type=coaching_type,
        context_snapshot=context_snapshot,
    )

    # Create a pending ChatMessage for the assistant's response
    assistant_message = ChatMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content="",
        status="pending",
    )

    # Prepare payload for ai-assistant
    payload = {
        "conversation_id": conversation.id,
        "user_context": context_snapshot,
        "coaching_type": coaching_type,
    }

    # Add user's custom LLM config if Premium+
    llm_config = _get_user_llm_config(user)
    if llm_config:
        payload["llm_config"] = llm_config

    def stream_proxy():
        """Proxy the SSE stream from ai-assistant."""
        full_response = []

        try:
            ai_url = f"{settings.AI_ASSISTANT_URL}/chat/start/stream"
            response = requests.post(ai_url, json=payload, stream=True, timeout=120)

            if response.status_code != 200:
                yield f"data: {json.dumps({'error': 'Service unavailable'})}\n\n"
                return

            for line in response.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    yield decoded + "\n"

                    # Extract token content to build full response
                    if decoded.startswith("data: ") and decoded != "data: [DONE]":
                        try:
                            token_data = json.loads(decoded[6:])
                            if "token" in token_data:
                                # Unescape newlines
                                token = token_data["token"].replace("\\n", "\n")
                                full_response.append(token)
                        except json.JSONDecodeError:
                            pass

            # Save the complete response
            assistant_message.content = "".join(full_response)
            assistant_message.status = "completed"
            assistant_message.save()

            logger.info(f"Streaming completed for conversation {conversation.id}")

        except requests.RequestException as e:
            logger.error(f"Streaming failed: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            assistant_message.status = "failed"
            assistant_message.save()

    # Return conversation_id in first event
    def wrapped_stream():
        yield f"data: {json.dumps({'conversation_id': conversation.id, 'message_id': assistant_message.id})}\n\n"
        yield from stream_proxy()

    return StreamingHttpResponse(
        wrapped_stream(),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@login_required
@require_POST
def chat_message_stream_view(request):
    """Send a message and get a streaming response.

    Proxies SSE stream from ai-assistant to the frontend.
    """
    import json

    from django.http import StreamingHttpResponse

    try:
        data = json.loads(request.body)
        conversation_id = data.get("conversation_id")
        message_content = data.get("message", "").strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"success": False, "error": "Données invalides"}, status=400)

    if not message_content:
        return JsonResponse({"success": False, "error": "Message vide"}, status=400)

    # Get conversation
    try:
        conversation = ChatConversation.objects.get(id=conversation_id, user=request.user)
    except ChatConversation.DoesNotExist:
        return JsonResponse({"success": False, "error": "Conversation non trouvée"}, status=404)

    # Save user message
    user_message = ChatMessage.objects.create(
        conversation=conversation,
        role="user",
        content=message_content,
        status="completed",
    )

    # Create pending assistant message
    assistant_message = ChatMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content="",
        status="pending",
    )

    # Build history from previous messages
    history = []
    for msg in conversation.get_messages().exclude(id=assistant_message.id):
        if msg.status == "completed" and msg.content:
            history.append({"role": msg.role, "content": msg.content})

    # Prepare payload
    user_context = conversation.context_snapshot or _build_user_context(
        request.user, coaching_type=conversation.coaching_type
    )
    payload = {
        "conversation_id": conversation.id,
        "message": message_content,
        "history": history,
        "user_context": user_context,
        "coaching_type": conversation.coaching_type,
    }

    # Add user's custom LLM config if Premium+
    llm_config = _get_user_llm_config(request.user)
    if llm_config:
        payload["llm_config"] = llm_config

    def stream_proxy():
        """Proxy the SSE stream from ai-assistant."""
        full_response = []

        try:
            ai_url = f"{settings.AI_ASSISTANT_URL}/chat/message/stream"
            response = requests.post(ai_url, json=payload, stream=True, timeout=120)

            if response.status_code != 200:
                yield f"data: {json.dumps({'error': 'Service unavailable'})}\n\n"
                return

            for line in response.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    yield decoded + "\n"

                    # Extract token content
                    if decoded.startswith("data: ") and decoded != "data: [DONE]":
                        try:
                            token_data = json.loads(decoded[6:])
                            if "token" in token_data:
                                token = token_data["token"].replace("\\n", "\n")
                                full_response.append(token)
                        except json.JSONDecodeError:
                            pass

            # Save the complete response
            assistant_message.content = "".join(full_response)
            assistant_message.status = "completed"
            assistant_message.save()

            logger.info(f"Streaming message completed for conversation {conversation.id}")

        except requests.RequestException as e:
            logger.error(f"Streaming message failed: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            assistant_message.status = "failed"
            assistant_message.save()

    # Return message IDs in first event
    def wrapped_stream():
        yield f"data: {json.dumps({'user_message_id': user_message.id, 'assistant_message_id': assistant_message.id})}\n\n"
        yield from stream_proxy()

    return StreamingHttpResponse(
        wrapped_stream(),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@login_required
@require_GET
def success_list_view(request):
    """List user's professional successes."""
    successes = []
    for s in request.user.professional_successes.all():
        successes.append(
            {
                "id": s.id,
                "title": s.title,
                "situation": s.situation,
                "task": s.task,
                "action": s.action,
                "result": s.result,
                "skills_demonstrated": s.skills_demonstrated,
                "is_draft": s.is_draft,
                "is_active": s.is_active,
                "is_complete": s.is_complete(),
                "completion_percentage": s.get_completion_percentage(),
                "created_at": s.created_at.isoformat(),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "successes": successes,
        }
    )


@login_required
@require_POST
def success_create_view(request):
    """Create a professional success from STAR data."""
    import json

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Données invalides"}, status=400)

    title = data.get("title", "").strip()
    if not title:
        return JsonResponse({"success": False, "error": "Le titre est requis"}, status=400)

    # Optional: link to conversation
    conversation_id = data.get("conversation_id")
    source_conversation = None
    if conversation_id:
        with contextlib.suppress(ChatConversation.DoesNotExist):
            source_conversation = ChatConversation.objects.get(id=conversation_id, user=request.user)

    success = ProfessionalSuccess.objects.create(
        user=request.user,
        title=title,
        situation=data.get("situation", ""),
        task=data.get("task", ""),
        action=data.get("action", ""),
        result=data.get("result", ""),
        skills_demonstrated=data.get("skills_demonstrated", []),
        source_conversation=source_conversation,
        is_draft=data.get("is_draft", True),
    )

    logger.info(f"ProfessionalSuccess {success.id} created for user {request.user.id}")

    return JsonResponse(
        {
            "success": True,
            "success_id": success.id,
            "title": success.title,
            "is_complete": success.is_complete(),
        }
    )


@login_required
@require_POST
def success_update_view(request, success_id):
    """Update a professional success."""
    import json

    try:
        success = ProfessionalSuccess.objects.get(id=success_id, user=request.user)
    except ProfessionalSuccess.DoesNotExist:
        return JsonResponse({"success": False, "error": "Succès non trouvé"}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Données invalides"}, status=400)

    # Update fields
    if "title" in data:
        success.title = data["title"]
    if "situation" in data:
        success.situation = data["situation"]
    if "task" in data:
        success.task = data["task"]
    if "action" in data:
        success.action = data["action"]
    if "result" in data:
        success.result = data["result"]
    if "skills_demonstrated" in data:
        success.skills_demonstrated = data["skills_demonstrated"]
    if "is_draft" in data:
        success.is_draft = data["is_draft"]
    if "is_active" in data:
        success.is_active = data["is_active"]

    success.save()

    logger.info(f"ProfessionalSuccess {success.id} updated")

    return JsonResponse(
        {
            "success": True,
            "success_id": success.id,
            "is_complete": success.is_complete(),
        }
    )


@login_required
@require_http_methods(["DELETE", "POST"])
def success_delete_view(request, success_id):
    """Delete a professional success."""
    try:
        success = ProfessionalSuccess.objects.get(id=success_id, user=request.user)
    except ProfessionalSuccess.DoesNotExist:
        return JsonResponse({"success": False, "error": "Succès non trouvé"}, status=404)

    title = success.title
    success.delete()

    logger.info(f"ProfessionalSuccess '{title}' deleted by user {request.user.id}")

    return JsonResponse(
        {
            "success": True,
            "message": f"Succès '{title}' supprimé",
        }
    )


# ============================================================================
# Pitch Views
# ============================================================================


@login_required
@require_GET
def pitch_list_view(request):
    """List user's pitches."""
    pitches = []
    for p in request.user.pitches.all():
        pitches.append(
            {
                "id": p.id,
                "title": p.title or f"Pitch #{p.id}",
                "is_draft": p.is_draft,
                "is_default": p.is_default,
                "is_complete": p.is_complete(),
                "word_count_30s": p.get_word_count_30s(),
                "word_count_3min": p.get_word_count_3min(),
                "target_context": p.target_context,
                "created_at": p.created_at.isoformat(),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "pitches": pitches,
        }
    )


@login_required
@require_POST
def pitch_create_view(request):
    """Create a pitch from extracted data."""
    import json

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Données invalides"}, status=400)

    # Optional: link to conversation
    conversation_id = data.get("conversation_id")
    source_conversation = None
    if conversation_id:
        with contextlib.suppress(ChatConversation.DoesNotExist):
            source_conversation = ChatConversation.objects.get(id=conversation_id, user=request.user)

    pitch = Pitch.objects.create(
        user=request.user,
        title=data.get("title", ""),
        pitch_30s=data.get("pitch_30s", ""),
        pitch_3min=data.get("pitch_3min", ""),
        key_strengths=data.get("key_strengths", []),
        target_context=data.get("target_context", ""),
        source_conversation=source_conversation,
        is_draft=data.get("is_draft", True),
    )

    logger.info("Pitch %s created for user %s", pitch.id, request.user.id)

    return JsonResponse(
        {
            "success": True,
            "pitch_id": pitch.id,
            "is_complete": pitch.is_complete(),
        }
    )


@login_required
@require_POST
def pitch_update_view(request, pitch_id):
    """Update a pitch."""
    import json

    try:
        pitch = Pitch.objects.get(id=pitch_id, user=request.user)
    except Pitch.DoesNotExist:
        return JsonResponse({"success": False, "error": "Pitch non trouvé"}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Données invalides"}, status=400)

    # Update fields
    if "title" in data:
        pitch.title = data["title"]
    if "pitch_30s" in data:
        pitch.pitch_30s = data["pitch_30s"]
    if "pitch_3min" in data:
        pitch.pitch_3min = data["pitch_3min"]
    if "key_strengths" in data:
        pitch.key_strengths = data["key_strengths"]
    if "target_context" in data:
        pitch.target_context = data["target_context"]
    if "is_draft" in data:
        pitch.is_draft = data["is_draft"]
    if "is_default" in data:
        pitch.is_default = data["is_default"]

    pitch.save()

    logger.info(f"Pitch {pitch.id} updated")

    return JsonResponse(
        {
            "success": True,
            "pitch_id": pitch.id,
            "is_complete": pitch.is_complete(),
        }
    )


@login_required
@require_http_methods(["DELETE", "POST"])
def pitch_delete_view(request, pitch_id):
    """Delete a pitch."""
    try:
        pitch = Pitch.objects.get(id=pitch_id, user=request.user)
    except Pitch.DoesNotExist:
        return JsonResponse({"success": False, "error": "Pitch non trouvé"}, status=404)

    title = pitch.title or f"Pitch #{pitch.id}"
    pitch.delete()

    logger.info(f"Pitch '{title}' deleted by user {request.user.id}")

    return JsonResponse(
        {
            "success": True,
            "message": f"Pitch '{title}' supprimé",
        }
    )


@login_required
@require_GET
def pitch_detail_view(request, pitch_id):
    """Get a pitch's full details."""
    try:
        pitch = Pitch.objects.get(id=pitch_id, user=request.user)
    except Pitch.DoesNotExist:
        return JsonResponse({"success": False, "error": "Pitch non trouvé"}, status=404)

    return JsonResponse(
        {
            "success": True,
            "pitch": {
                "id": pitch.id,
                "title": pitch.title,
                "pitch_30s": pitch.pitch_30s,
                "pitch_3min": pitch.pitch_3min,
                "key_strengths": pitch.key_strengths,
                "target_context": pitch.target_context,
                "is_draft": pitch.is_draft,
                "is_default": pitch.is_default,
                "is_complete": pitch.is_complete(),
                "word_count_30s": pitch.get_word_count_30s(),
                "word_count_3min": pitch.get_word_count_3min(),
                "created_at": pitch.created_at.isoformat(),
                "updated_at": pitch.updated_at.isoformat(),
            },
        }
    )


@login_required
def applications_list_view(request):
    """Display all user's applications as cards."""
    applications = Application.objects.filter(user=request.user).select_related("imported_offer", "candidate_profile")

    # Group by status for potential filtering
    status_counts = {
        "all": applications.count(),
        "added": applications.filter(status="added").count(),
        "in_progress": applications.filter(status="in_progress").count(),
        "applied": applications.filter(status="applied").count(),
        "interview": applications.filter(status="interview").count(),
        "accepted": applications.filter(status="accepted").count(),
        "rejected": applications.filter(status="rejected").count(),
    }

    # Filter by status if requested
    status_filter = request.GET.get("status")
    if status_filter and status_filter != "all":
        applications = applications.filter(status=status_filter)

    context = {
        "applications": applications,
        "status_counts": status_counts,
        "current_filter": status_filter or "all",
    }
    return render(request, "accounts/applications_list.html", context)


@login_required
def application_detail_view(request, application_id):
    """Display detailed view of a single application."""
    application = (
        Application.objects.filter(id=application_id, user=request.user)
        .select_related("imported_offer", "candidate_profile")
        .first()
    )

    if not application:
        from django.http import Http404

        raise Http404("Candidature non trouvee")

    # Get user's DOCX template (or default) as JSON string
    docx_template_config = None
    user = request.user
    if user.docx_template:
        docx_template_config = json_module.dumps(user.docx_template.to_js_config())
    else:
        # Use default template if user has no preference
        default_template = DocxTemplate.objects.filter(is_default=True).first()
        if default_template:
            docx_template_config = json_module.dumps(default_template.to_js_config())

    context = {
        "application": application,
        "docx_template_config": docx_template_config,
    }
    return render(request, "accounts/application_detail.html", context)


@login_required
@require_POST
def application_update_status_view(request, application_id):
    """Update application status via AJAX or form."""
    application = Application.objects.filter(id=application_id, user=request.user).first()

    if not application:
        from django.http import Http404

        raise Http404("Candidature non trouvee")

    new_status = request.POST.get("status")
    valid_statuses = [choice[0] for choice in APPLICATION_STATUS_CHOICES]

    if new_status in valid_statuses:
        old_status = application.status
        application.status = new_status
        application.add_history_event(
            "status_changed",
            f"Statut change de {old_status} a {new_status}",
        )
        application.save()

    return redirect("accounts:application_detail", application_id=application.id)


@login_required
@require_POST
def application_update_notes_view(request, application_id):
    """Update application notes."""
    application = Application.objects.filter(id=application_id, user=request.user).first()

    if not application:
        from django.http import Http404

        raise Http404("Candidature non trouvee")

    notes = request.POST.get("notes", "")
    application.notes = notes
    if notes:
        application.add_history_event("note_added", "Notes mises a jour")
    application.save()

    return redirect("accounts:application_detail", application_id=application.id)


@login_required
@require_POST
def application_delete_view(request, application_id):
    """Delete an application."""
    application = Application.objects.filter(id=application_id, user=request.user).first()

    if not application:
        from django.http import Http404

        raise Http404("Candidature non trouvee")

    application.delete()
    return redirect("accounts:applications_list")


# --- CV and Cover Letter Generation Views ---


def _build_candidate_context(user, profile=None):
    """Build candidate context from user and profile for AI generation."""
    # Get experiences from extracted lines
    experiences = []
    for line in user.extracted_lines.filter(content_type="experience", is_active=True):
        experiences.append(
            {
                "entity": line.entity or "",
                "position": line.position or "",
                "dates": line.dates or "",
                "description": line.description or line.content or "",
            }
        )

    # Get education
    education = []
    for line in user.extracted_lines.filter(content_type="education", is_active=True):
        education.append(
            {
                "entity": line.entity or "",
                "degree": line.position or "",
                "dates": line.dates or "",
            }
        )

    # Get skills
    skills = []
    for line in user.extracted_lines.filter(content_type__in=["skill_hard", "skill_soft"], is_active=True):
        skills.append(line.content)

    # Get professional successes
    successes = []
    for success in user.professional_successes.filter(is_active=True):
        successes.append(
            {
                "title": success.title,
                "situation": success.situation,
                "task": success.task,
                "action": success.action,
                "result": success.result,
            }
        )

    # Get interests
    interests = []
    for line in user.extracted_lines.filter(content_type="interest", is_active=True):
        interests.append(line.content)

    # Get social links
    social_links = []
    for link in user.social_links.all().order_by("order"):
        social_links.append(
            {
                "name": link.get_link_type_display(),
                "url": link.url,
            }
        )

    return {
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "email": user.email or "",
        "phone": user.phone or "",
        "location": user.location or "",
        "experiences": experiences,
        "education": education,
        "skills": skills,
        "professional_successes": successes,
        "interests": interests,
        "social_links": social_links,
    }


def _build_job_offer_context(imported_offer):
    """Build job offer context from ImportedOffer for AI generation."""
    return {
        "title": imported_offer.title or "",
        "company": imported_offer.company or "",
        "location": imported_offer.location or "",
        "contract_type": imported_offer.contract_type or "",
        "remote_type": imported_offer.remote_type or "",
        "description": imported_offer.description or "",
        "skills": imported_offer.skills or [],
    }


@login_required
@require_POST
def application_generate_cv_view(request, application_id):
    """Trigger CV generation for an application."""
    import json as json_module

    application = (
        Application.objects.filter(id=application_id, user=request.user).select_related("imported_offer").first()
    )

    if not application:
        return JsonResponse({"error": "Candidature non trouvee"}, status=404)

    # Parse request body for adaptation level
    adaptation_level = 2  # Default value
    if request.body:
        with contextlib.suppress(json_module.JSONDecodeError):
            body_data = json_module.loads(request.body)
            adaptation_level = body_data.get("adaptation_level", 2)
            # Ensure it's within valid range
            adaptation_level = max(1, min(4, int(adaptation_level)))

    # Build contexts
    candidate_context = _build_candidate_context(request.user, application.candidate_profile)
    job_offer_context = _build_job_offer_context(application.imported_offer)

    # Call ai-assistant service
    ai_assistant_url = settings.AI_ASSISTANT_URL or "http://ai-assistant:8084"

    try:
        response = requests.post(
            f"{ai_assistant_url}/generate/cv",
            json={
                "application_id": application.id,
                "candidate": candidate_context,
                "job_offer": job_offer_context,
                "adaptation_level": adaptation_level,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        # Store task_id in application for polling
        application.add_history_event("cv_generation_started", f"Task ID: {data['task_id']}")
        application.save()

        return JsonResponse(
            {
                "task_id": data["task_id"],
                "message": "Generation du CV lancee",
            }
        )

    except requests.RequestException as e:
        logger.error(f"Failed to call ai-assistant for CV generation: {e}")
        return JsonResponse({"error": "Service IA indisponible"}, status=503)


@login_required
@require_POST
def application_generate_cover_letter_view(request, application_id):
    """Trigger cover letter generation for an application."""
    application = (
        Application.objects.filter(id=application_id, user=request.user).select_related("imported_offer").first()
    )

    if not application:
        return JsonResponse({"error": "Candidature non trouvee"}, status=404)

    # Build contexts
    candidate_context = _build_candidate_context(request.user, application.candidate_profile)
    job_offer_context = _build_job_offer_context(application.imported_offer)

    # Call ai-assistant service
    ai_assistant_url = settings.AI_ASSISTANT_URL or "http://ai-assistant:8084"

    try:
        response = requests.post(
            f"{ai_assistant_url}/generate/cover-letter",
            json={
                "application_id": application.id,
                "candidate": candidate_context,
                "job_offer": job_offer_context,
                "custom_cv": application.custom_cv or "",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        # Store task_id in application for polling
        application.add_history_event("cover_letter_generation_started", f"Task ID: {data['task_id']}")
        application.save()

        return JsonResponse(
            {
                "task_id": data["task_id"],
                "message": "Generation de la lettre lancee",
            }
        )

    except requests.RequestException as e:
        logger.error(f"Failed to call ai-assistant for cover letter generation: {e}")
        return JsonResponse({"error": "Service IA indisponible"}, status=503)


@login_required
@require_GET
def application_generation_status_view(request, application_id, task_id):
    """Poll for generation task status."""
    application = Application.objects.filter(id=application_id, user=request.user).first()

    if not application:
        return JsonResponse({"error": "Candidature non trouvee"}, status=404)

    # Call ai-assistant service for status
    ai_assistant_url = settings.AI_ASSISTANT_URL or "http://ai-assistant:8084"

    try:
        response = requests.get(
            f"{ai_assistant_url}/generate/status/{task_id}",
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        return JsonResponse(data)

    except requests.RequestException as e:
        logger.error(f"Failed to get generation status: {e}")
        return JsonResponse({"error": "Service IA indisponible"}, status=503)


@login_required
@require_POST
def application_save_cv_view(request, application_id):
    """Save generated CV content to application."""
    application = Application.objects.filter(id=application_id, user=request.user).first()

    if not application:
        return JsonResponse({"error": "Candidature non trouvee"}, status=404)

    import json as json_module

    try:
        data = json_module.loads(request.body)
        content = data.get("content", "")
    except json_module.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    application.custom_cv = content
    application.add_history_event("cv_generated", "CV personnalise genere")
    application.save()

    return JsonResponse({"success": True, "message": "CV enregistre"})


@login_required
@require_POST
def application_save_cover_letter_view(request, application_id):
    """Save generated cover letter content to application."""
    application = Application.objects.filter(id=application_id, user=request.user).first()

    if not application:
        return JsonResponse({"error": "Candidature non trouvee"}, status=404)

    import json as json_module

    try:
        data = json_module.loads(request.body)
        content = data.get("content", "")
    except json_module.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    application.cover_letter = content
    application.add_history_event("cover_letter_generated", "Lettre de motivation generee")
    application.save()

    return JsonResponse({"success": True, "message": "Lettre enregistree"})
