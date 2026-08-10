from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import HasFoundationPermission

from .models import Notification, NotificationPreference
from .serializers import NotificationPreferenceSerializer, NotificationSerializer
from .services import archive_notification, mark_all_read, mark_read, mark_unread


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "notifications.notification.view",
        "retrieve": "notifications.notification.view",
        "unread_count": "notifications.notification.view",
        "read": "notifications.notification.view",
        "unread": "notifications.notification.view",
        "read_all": "notifications.notification.view",
        "archive": "notifications.notification.view",
        "default": "notifications.notification.view",
    }
    filterset_fields = ["severity", "notification_type", "read_at"]
    search_fields = ["title", "message"]
    ordering_fields = ["created_at", "read_at", "severity"]

    def get_queryset(self):
        queryset = Notification.objects.filter(recipient_user=self.request.user)
        if self.request.query_params.get("include_archived") != "true":
            queryset = queryset.filter(archived_at__isnull=True)
        return queryset

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = self.get_queryset().filter(read_at__isnull=True).count()
        return Response({"count": count})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = mark_read(notification_id=self.get_object().pk, user=request.user)
        return Response(self.get_serializer(notification).data)

    @action(detail=True, methods=["post"])
    def unread(self, request, pk=None):
        notification = mark_unread(notification_id=self.get_object().pk, user=request.user)
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        return Response({"updated": mark_all_read(user=request.user)})

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        archive_notification(notification_id=self.get_object().pk, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationPreferenceViewSet(viewsets.GenericViewSet):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {"default": "notifications.notification.manage_preferences"}

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        if request.method == "PATCH":
            serializer = self.get_serializer(preference, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(self.get_serializer(preference).data)
