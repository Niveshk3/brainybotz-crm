from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("analytics/", views.analytics, name="analytics"),
    path("reports/<str:report_type>.csv", views.report_csv, name="report_csv"),
    path("", views.dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("otp/login/", views.otp_request, name="otp_request"),
    path("otp/verify/", views.otp_verify, name="otp_verify"),
    path("profile/", views.profile, name="profile"),
    path("password/change/", auth_views.PasswordChangeView.as_view(
        template_name="registration/password_change_form.html",
        success_url="/password/change/done/"
    ), name="password_change"),
    path("password/change/done/", auth_views.PasswordChangeDoneView.as_view(
        template_name="registration/password_change_done.html"
    ), name="password_change_done"),
    path("password/reset/", auth_views.PasswordResetView.as_view(
        template_name="registration/password_reset_form.html",
        email_template_name="registration/password_reset_email.txt",
        subject_template_name="registration/password_reset_subject.txt",
        success_url="/password/reset/done/"
    ), name="password_reset"),
    path("password/reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="registration/password_reset_done.html"
    ), name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="registration/password_reset_confirm.html",
        success_url="/password/reset/complete/"
    ), name="password_reset_confirm"),
    path("password/reset/complete/", auth_views.PasswordResetCompleteView.as_view(
        template_name="registration/password_reset_complete.html"
    ), name="password_reset_complete"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("students/", views.student_list, name="student_list"),
    path("students/add/", views.student_add, name="student_add"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", views.student_edit, name="student_edit"),

    path("classes/", views.class_list, name="class_list"),
    path("classes/<int:pk>/", views.class_detail, name="class_detail"),
    path("classes/<int:pk>/report/", views.class_report, name="class_report"),
    path("classes/<int:pk>/attendance/", views.mark_attendance, name="mark_attendance"),
    path("classes/<int:pk>/feedback/", views.add_feedback, name="add_feedback"),

    path("projects/", views.project_list, name="project_list"),
    path("projects/add/", views.project_add, name="project_add"),
    path("projects/<int:pk>/", views.project_detail, name="project_detail"),

    path("community/", views.community, name="community"),
    path("fees/", views.fees, name="fees"),
    path("fees/<int:pk>/pay/", views.create_razorpay_order, name="create_razorpay_order"),
    path("payments/verify/", views.verify_razorpay_payment, name="verify_razorpay_payment"),
    path("payments/webhook/", views.razorpay_webhook, name="razorpay_webhook"),
    path("payments/<int:pk>/receipt/", views.payment_receipt, name="payment_receipt"),
    path("certificates/", views.certificates, name="certificates"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/compose/", views.compose_notification, name="compose_notification"),
    path("notifications/<int:pk>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/read-all/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("employee-attendance/", views.employee_attendance, name="employee_attendance"),
]
