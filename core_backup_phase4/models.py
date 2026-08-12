from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from datetime import date


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    TRAINER = "TRAINER", "Trainer"
    STUDENT = "STUDENT", "Student"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to="profiles/", blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role})"


class Trainer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="trainer")
    employee_id = models.CharField(max_length=30, unique=True)
    specialization = models.CharField(max_length=150, blank=True)
    joining_date = models.DateField(default=date.today)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()}"


class Batch(models.Model):
    name = models.CharField(max_length=100)
    grade = models.CharField(max_length=50)
    branch = models.CharField(max_length=100)
    course_program = models.CharField(max_length=150, blank=True)
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, blank=True, related_name="batches")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - Grade {self.grade}"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student")
    student_id = models.CharField(max_length=30, unique=True, editable=False)
    full_name = models.CharField(max_length=200)
    photo = models.ImageField(upload_to="students/", blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=30, blank=True)
    grade = models.CharField(max_length=50)
    school = models.CharField(max_length=200, blank=True)
    junior_senior = models.CharField(max_length=30, blank=True)
    date_of_admission = models.DateField(default=date.today)
    branch = models.CharField(max_length=100)
    course_program = models.CharField(max_length=150, blank=True)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    address = models.TextField(blank=True)
    father_name = models.CharField(max_length=150, blank=True)
    father_contact = models.CharField(max_length=30, blank=True)
    father_occupation = models.CharField(max_length=150, blank=True)
    mother_name = models.CharField(max_length=150, blank=True)
    mother_contact = models.CharField(max_length=30, blank=True)
    mother_occupation = models.CharField(max_length=150, blank=True)
    aadhaar_number = models.CharField(max_length=20, blank=True)
    registered_contact = models.CharField(max_length=30, blank=True)
    active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = f"BB{timezone.now().strftime('%Y%m%d%H%M%S%f')[-10:]}"
        super().save(*args, **kwargs)

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    @property
    def attendance_percentage(self):
        total = self.attendances.count()
        if not total:
            return 0
        present = self.attendances.filter(status="PRESENT").count()
        return round(present * 100 / total, 1)

    def __str__(self):
        return f"{self.student_id} - {self.full_name}"


class ClassSession(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="classes")
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, related_name="classes")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    topic = models.CharField(max_length=200, blank=True)
    activity = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-start_time"]

    def __str__(self):
        return f"{self.date} - {self.batch.name} - {self.topic}"


class ClassReport(models.Model):
    session = models.OneToOneField(ClassSession, on_delete=models.CASCADE, related_name="report")
    what_was_taught = models.TextField()
    what_students_did = models.TextField()
    skills_developed = models.TextField(blank=True)
    materials_used = models.TextField(blank=True)
    trainer_summary = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report: {self.session}"


class ClassMedia(models.Model):
    report = models.ForeignKey(ClassReport, on_delete=models.CASCADE, related_name="media")
    file = models.FileField(upload_to="class_media/")
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_video(self):
        return self.file.name.lower().endswith((".mp4", ".mov", ".avi", ".webm", ".mkv"))


class Attendance(models.Model):
    STATUS = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("LATE", "Late"),
        ("LEAVE", "Leave"),
    ]
    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name="attendances")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendances")
    status = models.CharField(max_length=20, choices=STATUS, default="PRESENT")
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "student"], name="unique_session_student_attendance")
        ]


class StudentFeedback(models.Model):
    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name="feedbacks")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="feedbacks")
    participation = models.PositiveSmallIntegerField(default=5)
    understanding = models.PositiveSmallIntegerField(default=5)
    practical_skills = models.PositiveSmallIntegerField(default=5)
    teamwork = models.PositiveSmallIntegerField(default=5)
    trainer_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "student"], name="unique_session_student_feedback")
        ]


class StudentProject(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=200)
    project_date = models.DateField(default=date.today)
    description = models.TextField()
    skills = models.TextField(blank=True)
    trainer_feedback = models.TextField(blank=True)
    video = models.FileField(upload_to="projects/videos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-project_date"]


class ProjectMedia(models.Model):
    project = models.ForeignKey(StudentProject, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="projects/photos/")


class Achievement(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="achievements")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    achievement_date = models.DateField(default=date.today)
    created_at = models.DateTimeField(auto_now_add=True)


class Certificate(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="certificates")
    title = models.CharField(max_length=200)
    certificate_type = models.CharField(max_length=100)
    issue_date = models.DateField(default=date.today)
    file = models.FileField(upload_to="certificates/", blank=True, null=True)


class FeePlan(models.Model):
    name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class StudentFee(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="fees")
    fee_plan = models.ForeignKey(FeePlan, on_delete=models.CASCADE, related_name="student_fees")
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[("PENDING", "Pending"), ("PARTIAL", "Partial"), ("PAID", "Paid")], default="PENDING")

    @property
    def pending_amount(self):
        return max(self.fee_plan.amount - self.paid_amount, 0)

    def refresh_status(self):
        if self.paid_amount <= 0:
            self.status = "PENDING"
        elif self.paid_amount < self.fee_plan.amount:
            self.status = "PARTIAL"
        else:
            self.status = "PAID"
        self.save(update_fields=["status"])


class RazorpayOrder(models.Model):
    STATUS = [
        ("CREATED", "Created"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
    ]

    student_fee = models.ForeignKey(StudentFee, on_delete=models.CASCADE, related_name="razorpay_orders")
    order_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=STATUS, default="CREATED")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.order_id} - {self.student_fee.student.full_name}"


class Payment(models.Model):
    STATUS = [
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    student_fee = models.ForeignKey(StudentFee, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, default="Manual")
    transaction_id = models.CharField(max_length=150, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, unique=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="SUCCESS")
    paid_at = models.DateTimeField(auto_now_add=True)
    receipt_number = models.CharField(max_length=50, unique=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"RCP{timezone.now().strftime('%Y%m%d%H%M%S%f')[-12:]}"
        super().save(*args, **kwargs)
        if self.status == "SUCCESS":
            self.student_fee.paid_amount = sum(
                p.amount for p in self.student_fee.payments.filter(status="SUCCESS")
            )
            self.student_fee.refresh_status()


class CommunityPost(models.Model):
    POST_TYPES = [
        ("ANNOUNCEMENT", "Announcement"),
        ("CHALLENGE", "Challenge"),
        ("COMPETITION", "Competition"),
        ("WORKSHOP", "Workshop"),
        ("EVENT", "Event"),
        ("ACHIEVEMENT", "Achievement"),
        ("PROJECT", "Project Showcase"),
        ("NEWS", "STEM News"),
    ]
    title = models.CharField(max_length=200)
    post_type = models.CharField(max_length=30, choices=POST_TYPES)
    content = models.TextField()
    image = models.ImageField(upload_to="community/", blank=True, null=True)
    event_date = models.DateTimeField(blank=True, null=True)
    published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class EmployeeAttendance(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="employee_attendance")
    date = models.DateField(default=date.today)
    check_in = models.DateTimeField(blank=True, null=True)
    check_out = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[("PRESENT", "Present"), ("ABSENT", "Absent"), ("LATE", "Late"), ("LEAVE", "Leave")], default="PRESENT")

    @property
    def working_hours(self):
        if not self.check_in or not self.check_out:
            return 0
        seconds = (self.check_out - self.check_in).total_seconds()
        return round(seconds / 3600, 2)


class Notification(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="notifications",
        blank=True,
        null=True,
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="crm_notifications",
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default="GENERAL")
    action_url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
