from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
import csv
import json

from .models import (
    Student,
    Trainer,
    Batch,
    ClassSession,
    Attendance,
    StudentFee,
    Payment,
    StudentProject,
    Achievement,
)


def _role(user):
    try:
        return user.profile.role
    except Exception:
        return "ADMIN" if user.is_superuser else "STUDENT"


def _month_labels(n=6):
    today = timezone.localdate().replace(day=1)
    labels = []

    for i in range(n - 1, -1, -1):
        month = today.month - i
        year = today.year

        while month <= 0:
            month += 12
            year -= 1

        labels.append((year, month))

    return labels


def _field_exists(model, field_name):
    return any(
        field.name == field_name
        for field in model._meta.fields
    )


@login_required
def analytics(request):
    role = _role(request.user)

    if role == "STUDENT":
        return _student_analytics(request)

    if role == "TRAINER":
        return _trainer_analytics(request)

    return _admin_analytics(request)


def _admin_analytics(request):

    students = Student.objects.all()
    trainers = Trainer.objects.all()
    batches = Batch.objects.all()
    classes = ClassSession.objects.all()

    # Active counts
    if _field_exists(Student, "active"):
        active_students = students.filter(active=True).count()
    else:
        active_students = students.count()

    if _field_exists(Trainer, "active"):
        active_trainers = trainers.filter(active=True).count()
    else:
        active_trainers = trainers.count()

    if _field_exists(Batch, "active"):
        active_batches = batches.filter(active=True).count()
    else:
        active_batches = batches.count()

    # Attendance
    attendance_total = Attendance.objects.count()

    attendance_present = Attendance.objects.filter(
        status__in=["PRESENT", "LATE"]
    ).count()

    attendance_pct = (
        round((attendance_present / attendance_total) * 100, 1)
        if attendance_total
        else 0
    )

    # Fees
    fee_total = 0
    fee_paid = 0

    try:
        fee_total = (
            StudentFee.objects
            .select_related("fee_plan")
            .aggregate(
                total=Sum("fee_plan__amount")
            )
            .get("total")
            or 0
        )
    except Exception:
        pass

    try:
        fee_paid = (
            StudentFee.objects
            .aggregate(
                total=Sum("paid_amount")
            )
            .get("total")
            or 0
        )
    except Exception:
        try:
            fee_paid = (
                Payment.objects
                .aggregate(
                    total=Sum("amount")
                )
                .get("total")
                or 0
            )
        except Exception:
            fee_paid = 0

    fee_pending = max(
        float(fee_total) - float(fee_paid),
        0
    )

    # Monthly analytics
    months = _month_labels(6)

    month_labels = [
        f"{month:02d}/{year}"
        for year, month in months
    ]

    student_growth = []
    attendance_series = []
    payment_series = []

    for year, month in months:

        # Student growth
        if _field_exists(Student, "created_at"):
            new_students = (
                students
                .filter(
                    created_at__year=year,
                    created_at__month=month
                )
                .count()
            )
        else:
            new_students = 0

        student_growth.append(new_students)

        # Attendance trend
        monthly_attendance = Attendance.objects.filter(
            session__date__year=year,
            session__date__month=month
        )

        total = monthly_attendance.count()

        present = monthly_attendance.filter(
            status__in=["PRESENT", "LATE"]
        ).count()

        percentage = (
            round((present / total) * 100, 1)
            if total
            else 0
        )

        attendance_series.append(percentage)

        # Payment trend
        monthly_payment = 0

        if _field_exists(Payment, "created_at"):
            monthly_payment = (
                Payment.objects
                .filter(
                    created_at__year=year,
                    created_at__month=month
                )
                .aggregate(total=Sum("amount"))
                .get("total")
                or 0
            )

        payment_series.append(float(monthly_payment))

    # Batch distribution
    batch_data = []

    for batch in batches.order_by("name")[:12]:

        try:
            count = batch.students.count()
        except Exception:
            count = Student.objects.filter(
                batch=batch
            ).count()

        batch_data.append({
            "name": batch.name,
            "count": count,
        })

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
        "fee_pending": fee_pending,

        "month_labels": json.dumps(month_labels),
        "student_growth": json.dumps(student_growth),
        "attendance_series": json.dumps(attendance_series),
        "payment_series": json.dumps(payment_series),
        "batch_data": json.dumps(batch_data),
    }

    return render(
        request,
        "analytics/admin.html",
        context
    )


def _trainer_analytics(request):

    trainer = getattr(
        request.user,
        "trainer",
        None
    )

    if not trainer:
        return redirect("dashboard")

    sessions = ClassSession.objects.filter(
        trainer=trainer
    )

    attendance = Attendance.objects.filter(
        session__trainer=trainer
    )

    total = attendance.count()

    present = attendance.filter(
        status__in=["PRESENT", "LATE"]
    ).count()

    attendance_pct = (
        round((present / total) * 100, 1)
        if total
        else 0
    )

    # Get students through trainer's batches
    students = Student.objects.filter(
        batch__trainer=trainer
    )

    context = {
        "analytics_role": "TRAINER",
        "class_count": sessions.count(),
        "student_count": students.count(),
        "attendance_count": total,
        "attendance_pct": attendance_pct,
        "report_count": sessions.count(),
    }

    return render(
        request,
        "analytics/trainer.html",
        context
    )


def _student_analytics(request):

    student = getattr(
        request.user,
        "student",
        None
    )

    if not student:
        return redirect("dashboard")

    attendance = Attendance.objects.filter(
        student=student
    )

    total = attendance.count()

    present = attendance.filter(
        status__in=["PRESENT", "LATE"]
    ).count()

    absent = attendance.filter(
        status="ABSENT"
    ).count()

    attendance_pct = (
        round((present / total) * 100, 1)
        if total
        else 0
    )

    projects = StudentProject.objects.filter(
        student=student
    )

    achievements = Achievement.objects.filter(
        student=student
    )

    months = _month_labels(6)

    labels = [
        f"{month:02d}/{year}"
        for year, month in months
    ]

    series = []

    for year, month in months:

        monthly_attendance = attendance.filter(
            session__date__year=year,
            session__date__month=month
        )

        total_month = monthly_attendance.count()

        present_month = monthly_attendance.filter(
            status__in=["PRESENT", "LATE"]
        ).count()

        percentage = (
            round(
                (present_month / total_month) * 100,
                1
            )
            if total_month
            else 0
        )

        series.append(percentage)

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

    return render(
        request,
        "analytics/student.html",
        context
    )


@login_required
def report_csv(request, report_type):

    role = _role(request.user)

    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{report_type}_report.csv"'
    )

    writer = csv.writer(response)

    # -----------------------------
    # STUDENTS
    # -----------------------------

    if report_type == "students":

        writer.writerow([
            "Student ID",
            "Name",
            "Grade",
            "Branch",
            "School",
            "Status",
        ])

        students = Student.objects.all().order_by(
            "full_name"
        )

        for student in students:

            active = getattr(
                student,
                "active",
                True
            )

            writer.writerow([
                student.student_id,
                student.full_name,
                student.grade,
                student.branch,
                student.school,
                "Active" if active else "Inactive",
            ])

    # -----------------------------
    # ATTENDANCE
    # -----------------------------

    elif report_type == "attendance":

        writer.writerow([
            "Date",
            "Student",
            "Status",
            "Batch",
            "Trainer",
        ])

        attendance = (
            Attendance.objects
            .select_related(
                "student",
                "session",
                "session__batch",
                "session__trainer__user",
            )
            .order_by("-session__date")
        )

        if (
            role == "TRAINER"
            and hasattr(request.user, "trainer")
        ):
            attendance = attendance.filter(
                session__trainer=request.user.trainer
            )

        elif (
            role == "STUDENT"
            and hasattr(request.user, "student")
        ):
            attendance = attendance.filter(
                student=request.user.student
            )

        for item in attendance:

            trainer_name = ""

            try:
                trainer_name = (
                    item.session
                    .trainer
                    .user
                    .get_full_name()
                )
            except Exception:
                pass

            writer.writerow([
                item.session.date,
                item.student.full_name,
                item.status,
                item.session.batch.name,
                trainer_name,
            ])

    # -----------------------------
    # FEES
    # -----------------------------

    elif report_type == "fees":

        writer.writerow([
            "Student",
            "Fee Plan",
            "Amount",
            "Paid",
            "Pending",
            "Status",
        ])

        fees = StudentFee.objects.select_related(
            "student",
            "fee_plan"
        )

        if (
            role == "STUDENT"
            and hasattr(request.user, "student")
        ):
            fees = fees.filter(
                student=request.user.student
            )

        for fee in fees:

            amount = float(
                fee.fee_plan.amount
            )

            paid = float(
                getattr(
                    fee,
                    "paid_amount",
                    0
                ) or 0
            )

            pending = max(
                amount - paid,
                0
            )

            if paid >= amount:
                status = "PAID"
            elif paid > 0:
                status = "PARTIAL"
            else:
                status = "PENDING"

            writer.writerow([
                fee.student.full_name,
                fee.fee_plan.name,
                amount,
                paid,
                pending,
                status,
            ])

    # -----------------------------
    # PROJECTS
    # -----------------------------

    elif report_type == "projects":

        writer.writerow([
            "Student",
            "Project",
            "Status",
            "Created",
        ])

        projects = StudentProject.objects.select_related(
            "student"
        )

        if (
            role == "STUDENT"
            and hasattr(request.user, "student")
        ):
            projects = projects.filter(
                student=request.user.student
            )

        for project in projects:

            project_name = getattr(
                project,
                "title",
                None
            )

            if not project_name:
                project_name = getattr(
                    project,
                    "name",
                    ""
                )

            writer.writerow([
                project.student.full_name,
                project_name,
                getattr(
                    project,
                    "status",
                    ""
                ),
                getattr(
                    project,
                    "created_at",
                    ""
                ),
            ])

    else:

        writer.writerow([
            "Metric",
            "Value",
        ])

        writer.writerow([
            "Unsupported report",
            report_type,
        ])

    return response