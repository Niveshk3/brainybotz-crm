# BrainyBotz CRM

A Django-based Student CRM / Learning Management CRM based on the supplied BrainyBotz requirements.

## Included
- Role-based login: Admin, Trainer, Student
- Student profiles and guardian details
- Batches, trainers and classes
- Class reports with photos/videos
- Student-specific feedback
- Learning timeline
- Student STEM project portfolio
- Attendance and monthly attendance summary
- Fees, payments and receipts
- Certificates and achievements
- Community announcements/events/competitions/posts
- Employee attendance
- Notifications
- Django admin
- Responsive Bootstrap dashboard
- Optional Razorpay payment integration hook

## Run locally

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

The first superuser can create Staff/Admin/Trainer/Student records from Django Admin.

## Notes
- OTP, Google/Apple login and production SMS/push integrations require provider credentials and are intentionally isolated for later configuration.
- Razorpay settings are optional. Without credentials, the CRM still supports manual payment records.
- Media files are stored locally in development.
