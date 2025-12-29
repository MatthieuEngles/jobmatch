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
    # Chat AI Assistant (STAR coaching)
    path("api/chat/start/", views.chat_start_view, name="chat_start"),
    path("api/chat/message/", views.chat_message_view, name="chat_message"),
    path("api/chat/status/<str:task_id>/", views.chat_status_view, name="chat_status"),
    path("api/chat/history/<int:conversation_id>/", views.chat_history_view, name="chat_history"),
    # Streaming endpoints (SSE)
    path("api/chat/start/stream/", views.chat_start_stream_view, name="chat_start_stream"),
    path("api/chat/message/stream/", views.chat_message_stream_view, name="chat_message_stream"),
    # Professional successes
    path("api/successes/", views.success_list_view, name="success_list"),
    path("api/successes/create/", views.success_create_view, name="success_create"),
    path("api/successes/<int:success_id>/update/", views.success_update_view, name="success_update"),
    path("api/successes/<int:success_id>/delete/", views.success_delete_view, name="success_delete"),
    # Pitches
    path("api/pitches/", views.pitch_list_view, name="pitch_list"),
    path("api/pitches/create/", views.pitch_create_view, name="pitch_create"),
    path("api/pitches/<int:pitch_id>/", views.pitch_detail_view, name="pitch_detail"),
    path("api/pitches/<int:pitch_id>/update/", views.pitch_update_view, name="pitch_update"),
    path("api/pitches/<int:pitch_id>/delete/", views.pitch_delete_view, name="pitch_delete"),
    # Applications (candidatures)
    path("applications/", views.applications_list_view, name="applications_list"),
    path("applications/<int:application_id>/", views.application_detail_view, name="application_detail"),
    path(
        "applications/<int:application_id>/status/",
        views.application_update_status_view,
        name="application_update_status",
    ),
    path(
        "applications/<int:application_id>/notes/", views.application_update_notes_view, name="application_update_notes"
    ),
    path("applications/<int:application_id>/delete/", views.application_delete_view, name="application_delete"),
    # AI generation for applications
    path(
        "applications/<int:application_id>/generate/cv/",
        views.application_generate_cv_view,
        name="application_generate_cv",
    ),
    path(
        "applications/<int:application_id>/generate/cover-letter/",
        views.application_generate_cover_letter_view,
        name="application_generate_cover_letter",
    ),
    path(
        "applications/<int:application_id>/generate/status/<str:task_id>/",
        views.application_generation_status_view,
        name="application_generation_status",
    ),
    path("applications/<int:application_id>/save/cv/", views.application_save_cv_view, name="application_save_cv"),
    path(
        "applications/<int:application_id>/save/cover-letter/",
        views.application_save_cover_letter_view,
        name="application_save_cover_letter",
    ),
]
