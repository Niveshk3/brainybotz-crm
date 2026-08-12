
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
import csv
import json

from .models import (
    Student, Trainer, Batch, ClassSession, Attendance,
    FeePlan, StudentFee, Payment, Project, Achievement, Notification
)

def _role(user):
    try:
        return user.profile.role
    except Exception:
        return "ADMIN" if user.is_superuser else "STUDENT"


def _safe_count(model, **kwargs):
    try:
        return model.objects.filter(**kwargs).count()
    except Exception:
        return model.objects.count()


def _month_labels(n=6):
    today = timezone.localdate().replace(day=1)
    labels = []
    for i in range(n-1, -1, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        labels.append((year, month))
    return labels


def analytics(request):
    r = _role(request.user)

    if r == "STUDENT":
        return _student_analytics(request)
    if r == "TRAINER":
        return _trainer_analytics(request)
    return _admin_analytics(request)


def _admin_analytics(request):
    students = Student.objects.all()
    trainers = Trainer.objects.all()
    batches = Batch.objects.all()
    classes = ClassSession.objects.all()

    active_students = students.filter(active=True).count() if "active" in [f.name for f in Student._meta.fields] else students.count()
    active_trainers = trainers.filter(active=True).count() if "active" in [f.name for f in Trainer._meta.fields] else trainers.count()
    active_batches = batches.filter(active=True).count() if "active" in [f.name for f in Batch._meta.fields] else batches.count()

    attendance_total = Attendance.objects.count()
    attendance_present = Attendance.objects.filter(status__in=["PRESENT", "LATE"]).count()
    attendance_pct = round((attendance_present / attendance_total) * 100, 1) if attendance_total else 0

    fee_total = 0
    fee_paid = 0
    pending_accounts = 0
    try:
        fee_total = StudentFee.objects.aggregate(v=Sum("amount")).get("v") or 0
    except Exception:
        try:
            fee_total = StudentFee.objects.aggregate(v=Sum("fee_plan__amount")).get("v") or 0
        except Exception:
            pass

    try:
        fee_paid = StudentFee.objects.aggregate(v=Sum("paid_amount")).get("v") or 0
        pending_accounts = StudentFee.objects.filter(paid_amount__lt=Sum("amount")).count()
    except Exception:
        try:
            fee_paid = Payment.objects.aggregate(v=Sum("amount")).get("v") or 0
        except Exception:
            fee_paid = 0

    # Monthly series.
    months = _month_labels(6)
    month_labels = [f"{m:02d}/{y}" for y, m in months]
    student_growth = []
    attendance_series = []
    payment_series = []

    for year, month in months:
        student_growth.append(students.filter(created_at__year=year, created_at__month=month).count()
                               if any(f.name == "created_at" for f in Student._meta.fields) else 0)

        att = Attendance.objects.filter(session__date__year=year, session__date__month=month)
        total = att.count()
        present = att.filter(status__in=["PRESENT", "LATE"]).count()
        attendance_series.append(round((present / total) * 100, 1) if total else 0)

        try:
            payment_series.append(float(Payment.objects.filter(
                created_at__year=year, created_at__month=month
            ).aggregate(v=Sum("amount")).get("v") or 0))
        except Exception:
            payment_series.append(0)

    # Batch distribution.
    batch_data = []
    for b in batches.order_by("name")[:12]:
        try:
            count = b.students.count()
        except Exception:
            count = Student.objects.filter(batch=b).count()
        batch_data.append({"name": b.name, "count": count})

    context = {
        "analytics_role": "ADMIN",
        "total_students": students.count(),
        "active_students": active_students,
        "total_trainers": trainers.count(),
        "active_trainers": active_trainers,
        "total_batches": batches.count(),
        "active_batches": active_batches,
        "total_classes": classes.count(),
        "attendance_pct": attendance_pct,
        "fee_total": float(fee_total),
        "fee_paid": float(fee_paid),
        "fee_pending": max(float(fee_total) - float(fee_paid), 0),
        "pending_accounts": pending_accounts,
        "month_labels": json.dumps(month_labels),
        "student_growth": json.dumps(student_growth),
        "attendance_series": json.dumps(attendance_series),
        "payment_series": json.dumps(payment_series),
        "batch_data": json.dumps(batch_data),
    }
    return render(request, "analytics/admin.html", context)


def _trainer_analytics(request):
    trainer = getattr(request.user, "trainer", None)
    if not trainer:
        return redirect("dashboard")

    sessions = ClassSession.objects.filter(trainer=trainer)
    students = Student.objects.filter(batch__trainer=trainer) if any(f.name == "trainer" for f in Batch._meta.fields) else Student.objects.none()
    attendance = Attendance.objects.filter(session__trainer=trainer)

    total = attendance.count()
    present = attendance.filter(status__in=["PRESENT", "LATE"]).count()
    attendance_pct = round((present / total) * 100, 1) if total else 0

    context = {
        "analytics_role": "TRAINER",
        "class_count": sessions.count(),
        "student_count": students.count(),
        "attendance_count": total,
        "attendance_pct": attendance_pct,
        "report_count": _safe_count(ClassSession, trainer=trainer),
    }
    return render(request, "analytics/trainer.html", context)


def _student_analytics(request):
    student = getattr(request.user, "student", None)
    if not student:
        return redirect("dashboard")

    attendance = Attendance.objects.filter(student=student)
    total = attendance.count()
    present = attendance.filter(status__in=["PRESENT", "LATE"]).count()
    absent = attendance.filter(status="ABSENT").count()
    attendance_pct = round((present / total) * 100, 1) if total else 0

    projects = Project.objects.filter(student=student) if any(f.name == "student" for f in Project._meta.fields) else Project.objects.none()
    achievements = Achievement.objects.filter(student=student) if any(f.name == "student" for f in Achievement._meta.fields) else Achievement.objects.none()

    months = _month_labels(6)
    labels = [f"{m:02d}/{y}" for y, m in months]
    series = []
    for year, month in months:
        a = attendance.filter(session__date__year=year, session__date__month=month)
        t = a.count()
        p = a.filter(status__in=["PRESENT", "LATE"]).count()
        series.append(round((p/t)*100, 1) if t else 0)

    context = {
        "analytics_role": "STUDENT",
        "student": student,
        "attendance_pct": attendance_pct,
        "present_count": present,
        "absent_count": absent,
        "class_count": total,
        "project_count": projects.count(),
        "achievement_count": achievements.count(),
        "month_labels": json.dumps(labels),
        "attendance_series": json.dumps(series),
    }
    return render(request, "analytics/student.html", context)


@login_required
def report_csv(request, report_type):
    r = _role(request.user)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{report_type}_report.csv"'
    writer = csv.writer(response)

    if report_type == "students":
        writer.writerow(["Student ID", "Name", "Grade", "Branch", "School", "Status"])
        qs = Student.objects.all().order_by("full_name")
        for s in qs:
            active = getattr(s, "active", True)
            writer.writerow([s.student_id, s.full_name, s.grade, s.branch, s.school, "Active" if active else "Inactive"])

    elif report_type == "attendance":
        writer.writerow(["Date", "Student", "Status", "Batch", "Trainer"])
        qs = Attendance.objects.select_related("student", "session", "session__batch", "session__trainer__user").order_by("-session__date")
        if r == "TRAINER" and hasattr(request.user, "trainer"):
            qs = qs.filter(session__trainer=request.user.trainer)
        elif r == "STUDENT" and hasattr(request.user, "student"):
            qs = qs.filter(student=request.user.student)
        for a in qs:
            writer.writerow([
                a.session.date,
                a.student.full_name,
                a.status,
                getattr(a.session.batch, "name", ""),
                getattr(getattr(a.session.trainer, "user", None), "get_full_name", lambda: "")(),
            ])

    elif report_type == "fees":
        writer.writerow(["Student", "Fee Plan", "Amount", "Paid", "Pending", "Status"])
        qs = StudentFee.objects.select_related("student", "fee_plan").all()
        if r == "STUDENT" and hasattr(request.user, "student"):
            qs = qs.filter(student=request.user.student)
        for f in qs:
            amount = getattr(f, "amount", None) or getattr(f.fee_plan, "amount", 0)
            paid = getattr(f, "paid_amount", 0) or 0
            writer.writerow([
                f.student.full_name,
                getattr(f.fee_plan, "name", ""),
                amount,
                paid,
                max(float(amount)-float(paid), 0),
                "PAID" if float(paid) >= float(amount) else ("PARTIAL" if paid else "PENDING")
            ])

    elif report_type == "projects":
        writer.writerow(["Student", "Project", "Status", "Created"])
        qs = Project.objects.all()
        if r == "STUDENT" and hasattr(request.user, "student") and any(f.name == "student" for f in Project._meta.fields):
            qs = qs.filter(student=request.user.student)
        for p in qs:
            writer.writerow([
                getattr(getattr(p, "student", None), "full_name", ""),
                getattr(p, "title", getattr(p, "name", "")),
                getattr(p, "status", ""),
                getattr(p, "created_at", ""),
            ])
    else:
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Unsupported report", report_type])

    return response
