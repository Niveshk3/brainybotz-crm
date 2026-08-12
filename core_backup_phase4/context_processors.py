from .models import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {"unread_notifications": 0}

    if hasattr(request.user, "student"):
        count = Notification.objects.filter(
            student=request.user.student, is_read=False
        ).count()
    else:
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()

    return {"unread_notifications": count}
