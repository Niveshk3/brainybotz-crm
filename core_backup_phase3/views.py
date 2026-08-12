from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
import json
import razorpay


from .forms import (
    StudentForm, ClassReportForm, FeedbackForm, ProjectForm,
    MultipleMediaForm
)
from .models import (
    Student, Trainer, Batch, ClassSession, ClassReport, Attendance,
    StudentFeedback, StudentProject, CommunityPost, StudentFee,
    Certificate, Notification, EmployeeAttendance, ClassMedia, Payment, RazorpayOrder
)


def role(user):
    if user.is_superuser:
        return "ADMIN"
    return getattr(getattr(user, "profile", None), "role", "STUDENT")


def can_manage_session(user, session):
    return role(user) == "ADMIN" or (
        role(user) == "TRAINER" and hasattr(user, "trainer")
        and session.trainer_id == user.trainer.id
    )


@login_required
def dashboard(request):
    r = role(request.user)
    context = {"role": r}

    if r == "STUDENT" and hasattr(request.user, "student"):
        student = request.user.student
        context.update({
            "student": student,
            "upcoming": ClassSession.objects.filter(
                batch=student.batch, date__gte=timezone.localdate()
            ).order_by("date", "start_time")[:5],
            "recent_classes": ClassSession.objects.filter(
                batch=student.batch
            ).order_by("-date", "-start_time")[:5],
            "achievements": student.achievements.all()[:5],
            "notifications": student.notifications.all()[:5],
            "projects": student.projects.all()[:5],
        })
        return render(request, "student_dashboard.html", context)

    if r == "TRAINER" and hasattr(request.user, "trainer"):
        trainer = request.user.trainer
        context.update({
            "trainer": trainer,
            "today_classes": ClassSession.objects.filter(
                trainer=trainer, date=timezone.localdate()
            ).order_by("start_time"),
            "batches": trainer.batches.filter(active=True),
        })
        return render(request, "trainer_dashboard.html", context)

    context.update({
        "student_count": Student.objects.filter(active=True).count(),
        "trainer_count": Trainer.objects.filter(active=True).count(),
        "batch_count": Batch.objects.filter(active=True).count(),
        "class_count": ClassSession.objects.count(),
        "pending_fees": StudentFee.objects.exclude(status="PAID").count(),
        "recent_posts": CommunityPost.objects.filter(published=True)[:5],
        "counts": [
            ("Students", Student.objects.filter(active=True).count()),
            ("Trainers", Trainer.objects.filter(active=True).count()),
            ("Batches", Batch.objects.filter(active=True).count()),
            ("Classes", ClassSession.objects.count()),
        ],
    })
    return render(request, "admin_dashboard.html", context)


@login_required
def student_list(request):
    q = request.GET.get("q", "").strip()
    students = Student.objects.select_related("batch").all()
    if role(request.user) == "TRAINER":
        students = students.filter(batch__trainer=request.user.trainer)
    elif role(request.user) == "STUDENT":
        students = students.filter(pk=request.user.student.pk)

    if q:
        students = students.filter(
            Q(full_name__icontains=q) |
            Q(student_id__icontains=q) |
            Q(school__icontains=q) |
            Q(branch__icontains=q)
        )
    return render(request, "students/list.html", {"students": students, "q": q})


@login_required
def student_add(request):
    if role(request.user) != "ADMIN":
        return redirect("dashboard")

    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            # Create a username from the supplied name; admin can change it later.
            full_name = form.cleaned_data["full_name"].strip()
            base = "".join(ch.lower() for ch in full_name if ch.isalnum())[:20] or "student"
            username = base
            counter = 1
            while User.objects.filter(username=username).exists():
                counter += 1
                username = f"{base}{counter}"

            user = User.objects.create_user(
                username=username,
                first_name=full_name.split()[0],
                last_name=" ".join(full_name.split()[1:]),
            )
            user.profile.role = "STUDENT"
            user.profile.phone = form.cleaned_data.get("registered_contact", "")
            user.profile.save()

            student = form.save(commit=False)
            student.user = user
            student.save()

            messages.success(request, f"Student created. Login username: {username}")
            return redirect("student_detail", pk=student.pk)
    else:
        form = StudentForm()

    return render(request, "form.html", {"form": form, "title": "Add Student"})


@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    r = role(request.user)

    if r == "STUDENT" and request.user.student.pk != student.pk:
        return redirect("dashboard")
    if r == "TRAINER" and student.batch_id and student.batch.trainer_id != request.user.trainer.id:
        return redirect("dashboard")

    timeline = []
    for c in ClassSession.objects.filter(batch=student.batch).order_by("-date", "-start_time"):
        feedback = StudentFeedback.objects.filter(session=c, student=student).first()
        attendance = Attendance.objects.filter(session=c, student=student).first()
        report = ClassReport.objects.filter(session=c).first()
        timeline.append((c, feedback, attendance, report))

    return render(request, "students/detail.html", {
        "student": student,
        "timeline": timeline,
        "projects": student.projects.all(),
        "achievements": student.achievements.all(),
        "certificates": student.certificates.all(),
        "fees": student.fees.select_related("fee_plan"),
    })


@login_required
def student_edit(request, pk):
    if role(request.user) != "ADMIN":
        return redirect("dashboard")

    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Student updated successfully.")
            return redirect("student_detail", pk=pk)
    else:
        form = StudentForm(instance=student)
    return render(request, "form.html", {"form": form, "title": "Edit Student"})


@login_required
def class_list(request):
    r = role(request.user)
    classes = ClassSession.objects.select_related("batch", "trainer")

    if r == "TRAINER":
        classes = classes.filter(trainer=request.user.trainer)
    elif r == "STUDENT":
        classes = classes.filter(batch=request.user.student.batch)

    return render(request, "classes/list.html", {"classes": classes})


@login_required
def class_detail(request, pk):
    session = get_object_or_404(
        ClassSession.objects.select_related("batch", "trainer"), pk=pk
    )
    r = role(request.user)

    if r == "STUDENT" and request.user.student.batch_id != session.batch_id:
        return redirect("dashboard")
    if r == "TRAINER" and session.trainer_id != request.user.trainer.id:
        return redirect("dashboard")

    return render(request, "classes/detail.html", {
        "session": session,
        "report": getattr(session, "report", None),
        "attendance": session.attendances.select_related("student"),
        "feedbacks": session.feedbacks.select_related("student"),
        "can_manage": can_manage_session(request.user, session),
    })


@login_required
def class_report(request, pk):
    session = get_object_or_404(ClassSession, pk=pk)

    if not can_manage_session(request.user, session):
        return redirect("dashboard")

    report = getattr(session, "report", None)

    if request.method == "POST":
        form = ClassReportForm(request.POST, instance=report)
        media_form = MultipleMediaForm(request.POST, request.FILES)

        if form.is_valid() and media_form.is_valid():
            obj = form.save(commit=False)
            obj.session = session
            obj.save()

            for uploaded in (media_form.cleaned_data.get("files") or []):
                ClassMedia.objects.create(report=obj, file=uploaded)

            messages.success(request, "Class report and media saved.")
            return redirect("class_detail", pk=pk)
    else:
        form = ClassReportForm(instance=report)
        media_form = MultipleMediaForm()

    return render(request, "classes/report_form.html", {
        "form": form,
        "media_form": media_form,
        "session": session,
        "report": report,
    })


@login_required
def mark_attendance(request, pk):
    session = get_object_or_404(ClassSession, pk=pk)

    if not can_manage_session(request.user, session):
        return redirect("dashboard")

    students = session.batch.students.filter(active=True)

    if request.method == "POST":
        for student in students:
            status = request.POST.get(f"status_{student.pk}", "ABSENT")
            Attendance.objects.update_or_create(
                session=session,
                student=student,
                defaults={"status": status},
            )
        messages.success(request, "Attendance submitted successfully.")
        return redirect("class_detail", pk=pk)

    existing = {a.student_id: a.status for a in session.attendances.all()}

    return render(request, "classes/attendance.html", {
        "session": session,
        "students": students,
        "existing": existing,
    })


@login_required
def add_feedback(request, pk):
    session = get_object_or_404(ClassSession, pk=pk)

    if not can_manage_session(request.user, session):
        return redirect("dashboard")

    student_id = request.GET.get("student")
    student = get_object_or_404(
        Student,
        pk=student_id,
        batch=session.batch,
        active=True,
    )

    feedback = StudentFeedback.objects.filter(
        session=session, student=student
    ).first()

    if request.method == "POST":
        form = FeedbackForm(request.POST, instance=feedback)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.session = session
            obj.student = student
            obj.save()
            messages.success(request, f"Feedback saved for {student.full_name}.")
            return redirect("class_detail", pk=pk)
    else:
        form = FeedbackForm(instance=feedback)

    return render(request, "classes/feedback_form.html", {
        "form": form,
        "session": session,
        "student": student,
    })


@login_required
def project_list(request):
    r = role(request.user)

    if r == "STUDENT":
        projects = request.user.student.projects.all()
    elif r == "TRAINER":
        projects = StudentProject.objects.filter(
            student__batch__trainer=request.user.trainer
        ).select_related("student")
    else:
        projects = StudentProject.objects.select_related("student").all()

    return render(request, "projects/list.html", {"projects": projects})


@login_required
def project_add(request):
    r = role(request.user)

    if r == "STUDENT":
        student = request.user.student
    elif r == "TRAINER":
        student_id = request.GET.get("student")
        if not student_id:
            messages.error(request, "Select a student before adding a project.")
            return redirect("student_list")
        student = get_object_or_404(
            Student,
            pk=student_id,
            batch__trainer=request.user.trainer,
        )
    elif r == "ADMIN":
        student_id = request.GET.get("student")
        if not student_id:
            messages.error(request, "Select a student before adding a project.")
            return redirect("student_list")
        student = get_object_or_404(Student, pk=student_id)
    else:
        return redirect("dashboard")

    if request.method == "POST":
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.student = student
            project.save()
            messages.success(request, "Project added to the student's STEM portfolio.")
            return redirect("project_detail", pk=project.pk)
    else:
        form = ProjectForm()

    return render(request, "form.html", {
        "form": form,
        "title": f"Add Project — {student.full_name}",
    })


@login_required
def project_detail(request, pk):
    project = get_object_or_404(
        StudentProject.objects.select_related("student"), pk=pk
    )
    r = role(request.user)

    if r == "STUDENT" and project.student_id != request.user.student.id:
        return redirect("dashboard")
    if r == "TRAINER" and project.student.batch.trainer_id != request.user.trainer.id:
        return redirect("dashboard")

    return render(request, "projects/detail.html", {"project": project})


@login_required
def community(request):
    posts = CommunityPost.objects.filter(published=True)
    return render(request, "community.html", {"posts": posts})


@login_required
def fees(request):
    if role(request.user) == "STUDENT":
        fee_items = request.user.student.fees.select_related("fee_plan")
    elif role(request.user) == "TRAINER":
        fee_items = StudentFee.objects.filter(
            student__batch__trainer=request.user.trainer
        ).select_related("student", "fee_plan")
    else:
        fee_items = StudentFee.objects.select_related("student", "fee_plan").all()

    return render(request, "fees.html", {"fees": fee_items})


@login_required
def certificates(request):
    if role(request.user) == "STUDENT":
        items = request.user.student.certificates.all()
    elif role(request.user) == "TRAINER":
        items = Certificate.objects.filter(
            student__batch__trainer=request.user.trainer
        ).select_related("student")
    else:
        items = Certificate.objects.select_related("student").all()

    return render(request, "certificates.html", {"certificates": items})


@login_required
def notifications(request):
    if role(request.user) == "STUDENT":
        items = request.user.student.notifications.all()
    else:
        items = Notification.objects.all()
    return render(request, "notifications.html", {"notifications": items})


@login_required
def employee_attendance(request):
    if role(request.user) != "ADMIN":
        return redirect("dashboard")

    items = EmployeeAttendance.objects.select_related(
        "employee"
    ).order_by("-date", "-check_in")

    return render(request, "employee_attendance.html", {"items": items})


def razorpay_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return None
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@login_required
def create_razorpay_order(request, pk):
    if request.method != "POST":
        return redirect("fees")

    if role(request.user) != "STUDENT":
        return redirect("dashboard")

    fee = get_object_or_404(
        StudentFee.objects.select_related("student", "fee_plan"),
        pk=pk,
        student=request.user.student,
    )

    pending = Decimal(str(fee.pending_amount))
    if pending <= 0:
        messages.info(request, "This fee is already fully paid.")
        return redirect("fees")

    client = razorpay_client()
    if client is None:
        messages.error(
            request,
            "Razorpay is not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to your environment."
        )
        return redirect("fees")

    receipt = f"BBFEE-{fee.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    data = {
        "amount": int(pending * 100),
        "currency": "INR",
        "receipt": receipt,
        "notes": {
            "student_id": fee.student.student_id,
            "fee_id": str(fee.pk),
        },
    }

    try:
        order = client.order.create(data=data)
    except Exception as exc:
        messages.error(request, f"Unable to create Razorpay order: {exc}")
        return redirect("fees")

    RazorpayOrder.objects.create(
        student_fee=fee,
        order_id=order["id"],
        amount=pending,
        currency="INR",
    )

    return render(request, "payments/checkout.html", {
        "fee": fee,
        "order": order,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "amount_paise": int(pending * 100),
        "student": fee.student,
    })


@login_required
def verify_razorpay_payment(request):
    if request.method != "POST" or role(request.user) != "STUDENT":
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=403)

    try:
        payload = json.loads(request.body)
        order_id = payload["razorpay_order_id"]
        payment_id = payload["razorpay_payment_id"]
        signature = payload["razorpay_signature"]
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"ok": False, "error": "Invalid payment payload"}, status=400)

    rp_order = get_object_or_404(
        RazorpayOrder.objects.select_related("student_fee__student"),
        order_id=order_id,
        student_fee__student=request.user.student,
    )

    if not settings.RAZORPAY_KEY_SECRET:
        return JsonResponse({"ok": False, "error": "Razorpay secret is not configured"}, status=500)

    client = razorpay_client()

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
    except Exception:
        rp_order.status = "FAILED"
        rp_order.save(update_fields=["status"])
        return JsonResponse({"ok": False, "error": "Payment signature verification failed"}, status=400)

    payment, created = Payment.objects.get_or_create(
        razorpay_payment_id=payment_id,
        defaults={
            "student_fee": rp_order.student_fee,
            "amount": rp_order.amount,
            "payment_method": "Razorpay",
            "transaction_id": payment_id,
            "razorpay_order_id": order_id,
            "razorpay_signature": signature,
            "status": "SUCCESS",
        },
    )

    if not created and payment.status != "SUCCESS":
        payment.status = "SUCCESS"
        payment.save(update_fields=["status"])

    rp_order.status = "PAID"
    rp_order.paid_at = timezone.now()
    rp_order.save(update_fields=["status", "paid_at"])

    Notification.objects.create(
        student=request.user.student,
        title="Fee Payment Successful",
        message=f"Payment of ₹{payment.amount} received. Receipt: {payment.receipt_number}",
        notification_type="FEE_PAYMENT",
    )

    return JsonResponse({
        "ok": True,
        "receipt": payment.receipt_number,
        "redirect": f"/payments/{payment.pk}/receipt/",
    })


@csrf_exempt
def razorpay_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    if not settings.RAZORPAY_WEBHOOK_SECRET:
        return HttpResponseBadRequest("Webhook secret not configured")

    signature = request.headers.get("X-Razorpay-Signature", "")
    try:
        client = razorpay_client()
        client.utility.verify_webhook_signature(
            request.body.decode("utf-8"),
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET,
        )
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid webhook signature")

    event = payload.get("event", "")
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

    if event in ("payment.captured", "order.paid"):
        payment_id = entity.get("id")
        order_id = entity.get("order_id")
        if payment_id and order_id:
            rp_order = RazorpayOrder.objects.filter(order_id=order_id).select_related("student_fee__student").first()
            if rp_order:
                payment, created = Payment.objects.get_or_create(
                    razorpay_payment_id=payment_id,
                    defaults={
                        "student_fee": rp_order.student_fee,
                        "amount": Decimal(str(entity.get("amount", 0))) / Decimal("100"),
                        "payment_method": "Razorpay",
                        "transaction_id": payment_id,
                        "razorpay_order_id": order_id,
                        "status": "SUCCESS",
                    },
                )
                rp_order.status = "PAID"
                rp_order.paid_at = timezone.now()
                rp_order.save(update_fields=["status", "paid_at"])

    return JsonResponse({"status": "ok"})


@login_required
def payment_receipt(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related("student_fee__student", "student_fee__fee_plan"),
        pk=pk,
        status="SUCCESS",
    )
    r = role(request.user)
    if r == "STUDENT" and payment.student_fee.student_id != request.user.student.id:
        return redirect("dashboard")
    if r == "TRAINER" and payment.student_fee.student.batch.trainer_id != request.user.trainer.id:
        return redirect("dashboard")
    return render(request, "payments/receipt.html", {"payment": payment})
