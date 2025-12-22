from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import UserProfileForm, UserRegistrationForm
from .models import User


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
    experiences = user.extracted_lines.filter(
        content_type="experience", is_active=True
    ).order_by("order", "-created_at")
    skills_hard = user.extracted_lines.filter(
        content_type="skill_hard", is_active=True
    ).order_by("order", "-created_at")
    skills_soft = user.extracted_lines.filter(
        content_type="skill_soft", is_active=True
    ).order_by("order", "-created_at")
    educations = user.extracted_lines.filter(
        content_type="education", is_active=True
    ).order_by("order", "-created_at")
    certifications = user.extracted_lines.filter(
        content_type="certification", is_active=True
    ).order_by("order", "-created_at")

    context = {
        "form": form,
        "experiences": experiences,
        "skills_hard": skills_hard,
        "skills_soft": skills_soft,
        "educations": educations,
        "certifications": certifications,
    }
    return render(request, "accounts/profile.html", context)


@login_required
def delete_account_view(request):
    if request.method == "POST":
        request.user.delete()
        return redirect("home")
    return render(request, "accounts/delete_account.html")
