from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification


def send_notification(user, type, title, message, data=None):
    """
    Creates a notification in the DB and sends it via WebSocket.
    Use this everywhere a notification should fire.
    """
    # Save to database
    notification = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        message=message,
        data=data or {},
    )

    # Send via WebSocket so user sees it instantly if online
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'user_{user.id}',
                {
                    'type': 'new_notification',
                    'notification': {
                        'id': str(notification.id),
                        'type': notification.type,
                        'title': notification.title,
                        'message': notification.message,
                        'is_read': notification.is_read,
                        'data': notification.data,
                        'created_at': notification.created_at.isoformat(),
                    }
                }
            )
    except Exception as e:
        print(f"WebSocket notify failed: {e}")

    return notification