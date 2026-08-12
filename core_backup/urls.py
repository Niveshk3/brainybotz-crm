from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
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
    path("certificates/", views.certificates, name="certificates"),
    path("notifications/", views.notifications, name="notifications"),
    path("employee-attendance/", views.employee_attendance, name="employee_attendance"),
]
