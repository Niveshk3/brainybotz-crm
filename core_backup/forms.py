from django import forms
from .models import (
    Student, ClassReport, StudentFeedback, StudentProject,
    CommunityPost, Attendance, Payment
)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if isinstance(data, (list, tuple)):
            return [super().clean(item, initial) for item in data]
        return super().clean(data, initial)


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        exclude = ["user", "student_id"]


class ClassReportForm(forms.ModelForm):
    class Meta:
        model = ClassReport
        exclude = ["session"]
        widgets = {
            "what_was_taught": forms.Textarea(attrs={"rows": 4}),
            "what_students_did": forms.Textarea(attrs={"rows": 4}),
            "skills_developed": forms.Textarea(attrs={"rows": 3}),
            "materials_used": forms.Textarea(attrs={"rows": 3}),
            "trainer_summary": forms.Textarea(attrs={"rows": 3}),
        }


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = StudentFeedback
        exclude = ["session", "student"]
        widgets = {
            "participation": forms.Select(choices=[(i, "⭐" * i) for i in range(1, 6)]),
            "understanding": forms.Select(choices=[(i, "⭐" * i) for i in range(1, 6)]),
            "practical_skills": forms.Select(choices=[(i, "⭐" * i) for i in range(1, 6)]),
            "teamwork": forms.Select(choices=[(i, "⭐" * i) for i in range(1, 6)]),
            "trainer_comment": forms.Textarea(attrs={"rows": 4}),
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = StudentProject
        exclude = ["student"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "skills": forms.Textarea(attrs={"rows": 3}),
            "trainer_feedback": forms.Textarea(attrs={"rows": 4}),
        }


class CommunityPostForm(forms.ModelForm):
    class Meta:
        model = CommunityPost
        fields = ["title", "post_type", "content", "image", "event_date", "published"]


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ["status"]


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "payment_method", "transaction_id"]


class MultipleMediaForm(forms.Form):
    files = MultipleFileField(
        required=False,
        label="Photos / Videos",
        widget=MultipleFileInput(attrs={
            "multiple": True,
            "accept": "image/*,video/*",
        }),
    )
