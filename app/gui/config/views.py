"""
Views for the main config app (home page, etc.)
"""

from django.views.generic import TemplateView


class HomeView(TemplateView):
    """
    Home page view that displays recent applications for authenticated users.
    """

    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            # Import here to avoid circular imports
            from accounts.models import Application

            # Get all applications for the user (scrollable list)
            recent_applications = Application.objects.filter(user=self.request.user).select_related("imported_offer")

            context["recent_applications"] = recent_applications
            context["applications_count"] = Application.objects.filter(user=self.request.user).count()

        return context
