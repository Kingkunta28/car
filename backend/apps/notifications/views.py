from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.utils import audit

from . import services
from .models import NotificationLog
from .serializers import NotificationSerializer


class AdminNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    filterset_fields = ["delivery_status", "notification_type", "booking"]
    search_fields = ["recipient", "booking__booking_reference", "invoice__invoice_number"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return NotificationLog.objects.select_related("booking", "invoice")

    @action(detail=True, methods=["post"])
    def resend(self, request, pk=None):
        log = self.get_object()
        new = services.resend(log)
        audit("notification.resent", actor=request.user, target=log, request=request, summary=log.recipient)
        return Response(NotificationSerializer(new).data if new else {"queued": False})
