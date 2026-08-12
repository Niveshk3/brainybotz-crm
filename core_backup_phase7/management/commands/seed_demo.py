from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile, Trainer, Batch, Student

class Command(BaseCommand):
    help = "Create demo BrainyBotz users and data"

    def handle(self, *args, **kwargs):
        admin, _ = User.objects.get_or_create(username="admin", defaults={"is_staff": True, "is_superuser": True})
        admin.set_password("Admin@123")
        admin.is_staff = admin.is_superuser = True
        admin.save()
        admin.profile.role = "ADMIN"
        admin.profile.save()

        trainer_user, _ = User.objects.get_or_create(username="trainer1", defaults={"first_name":"Demo","last_name":"Trainer"})
        trainer_user.set_password("Trainer@123")
        trainer_user.save()
        trainer_user.profile.role = "TRAINER"
        trainer_user.profile.save()
        trainer, _ = Trainer.objects.get_or_create(user=trainer_user, defaults={"employee_id":"TR001","specialization":"STEM & Robotics"})

        batch, _ = Batch.objects.get_or_create(name="Grade 5-8 Senior", defaults={"grade":"5-8","branch":"Main Branch","course_program":"STEM"})
        batch.trainer = trainer
        batch.save()

        student_user, _ = User.objects.get_or_create(username="student1", defaults={"first_name":"Demo","last_name":"Student"})
        student_user.set_password("Student@123")
        student_user.save()
        student_user.profile.role = "STUDENT"
        student_user.profile.save()
        student, _ = Student.objects.get_or_create(user=student_user, defaults={
            "full_name":"Demo Student","grade":"6","branch":"Main Branch","school":"BrainyBotz School","batch":batch
        })
        student.batch = batch
        student.save()

        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write("Admin: admin / Admin@123")
        self.stdout.write("Trainer: trainer1 / Trainer@123")
        self.stdout.write("Student: student1 / Student@123")
