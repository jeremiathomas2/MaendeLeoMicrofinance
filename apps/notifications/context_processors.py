def unread_notifications(request):
    if not request.user.is_authenticated:
        return {'unread_notifications': []}
    return {
        'unread_notifications': list(
            request.user.notifications.filter(is_read=False)[:5]
        ),
        'unread_count': request.user.notifications.filter(is_read=False).count(),
    }
