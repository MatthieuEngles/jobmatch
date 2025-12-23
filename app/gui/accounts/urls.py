from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("register/", views.UserRegistrationView.as_view(), name="register"),
    path("profile/", views.profile_view, name="profile"),
    path("settings/", views.account_settings_view, name="settings"),
    path("delete/", views.delete_account_view, name="delete"),
    path("export/", views.export_data_view, name="export_data"),
    path("cv/upload/", views.cv_upload_view, name="cv_upload"),
    path("cv/status/<str:task_id>/", views.cv_status_view, name="cv_status"),
    path("cv/delete/<int:cv_id>/", views.cv_delete_view, name="cv_delete"),
    path("photo/upload/", views.photo_upload_view, name="photo_upload"),
    path("photo/delete/", views.photo_delete_view, name="photo_delete"),
    path("social-link/add/", views.social_link_add_view, name="social_link_add"),
    path(
        "social-link/<int:link_id>/delete/",
        views.social_link_delete_view,
        name="social_link_delete",
    ),
    path("line/toggle/<int:line_id>/", views.extracted_line_toggle_view, name="line_toggle"),
    path("pricing/", views.pricing_view, name="pricing"),
    # Candidate profile management
    path("candidate-profile/switch/", views.profile_switch_view, name="profile_switch"),
    path("candidate-profile/create/", views.profile_create_view, name="profile_create"),
    path("candidate-profile/<int:profile_id>/update/", views.profile_update_view, name="profile_update"),
    path("candidate-profile/<int:profile_id>/delete/", views.profile_delete_view, name="profile_delete"),
    path("candidate-profile/<int:profile_id>/selections/", views.profile_selections_view, name="profile_selections"),
    path(
        "candidate-profile/<int:profile_id>/item/<int:line_id>/toggle/",
        views.profile_item_toggle_view,
        name="profile_item_toggle",
    ),
]
