from django.contrib import admin
from .models import *

admin.site.site_header = "BrainyBotz CRM Administration"
admin.site.site_title = "BrainyBotz CRM"
admin.site.index_title = "Management Dashboard"

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "notification_type", "student", "recipient", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("title", "message", "student__full_name", "recipient__username")


for model in [
    UserProfile, Trainer, Batch, Student, ClassSession, ClassReport, ClassMedia,
    Attendance, StudentFeedback, StudentProject, ProjectMedia, Achievement,
    Certificate, FeePlan, StudentFee, Payment, CommunityPost,
    EmployeeAttendance, RazorpayOrder
]:
    admin.site.register(model)
