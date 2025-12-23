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
    path("line/toggle/<int:line_id>/", views.extracted_line_toggle_view, name="line_toggle"),
    path("pricing/", views.pricing_view, name="pricing"),
]
