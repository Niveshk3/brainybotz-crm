from django.contrib import admin
from .models import *

admin.site.site_header = "BrainyBotz CRM Administration"
admin.site.site_title = "BrainyBotz CRM"
admin.site.index_title = "Management Dashboard"

for model in [
    UserProfile, Trainer, Batch, Student, ClassSession, ClassReport, ClassMedia,
    Attendance, StudentFeedback, StudentProject, ProjectMedia, Achievement,
    Certificate, FeePlan, StudentFee, Payment, CommunityPost,
    EmployeeAttendance, Notification, RazorpayOrder
]:
    admin.site.register(model)
