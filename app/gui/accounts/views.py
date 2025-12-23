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
    CV,
    SOCIAL_LINK_TYPE_CHOICES,
    CandidateProfile,
    ExtractedLine,
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
