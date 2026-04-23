from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification


class NotificationListView(APIView):
    """
    GET /api/notifications/
    Returns all notifications for the logged in user
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        unread_count = notifications.filter(is_read=False).count()

        data = [
            {
                'id': str(n.id),
                'type': n.type,
                'title': n.title,
                'message': n.message,
                'is_read': n.is_read,
                'data': n.data,
                'created_at': n.created_at.isoformat(),
            }
            for n in notifications[:50]  # latest 50
        ]

        return Response({
            'notifications': data,
            'unread_count': unread_count,
            'total': notifications.count(),
        })


class MarkNotificationReadView(APIView):
    """
    POST /api/notifications/<id>/read/
    Mark a single notification as read
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return Response({'message': 'Notification marked as read.'})
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found.'}, status=404)


class MarkAllReadView(APIView):
    """
    POST /api/notifications/read-all/
    Mark all notifications as read
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({'message': 'All notifications marked as read.'})


class DeleteNotificationView(APIView):
    """
    DELETE /api/notifications/<id>/delete/
    Delete a single notification
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            notification.delete()
            return Response({'message': 'Notification deleted.'})
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found.'}, status=404)