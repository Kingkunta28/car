import logging

import django_filters
from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import ALL_ROLES, FINANCE_ROLES
from apps.core.exceptions import BusinessRuleError
from apps.core.files import private_file_response
from apps.core.throttles import BookingAccessThrottle, BookingCreateThrottle, QuoteThrottle
from apps.core.utils import audit

from . import services
from .models import Booking, BookingDocument, BookingNote, BookingStatus, DocumentStatus, DocumentType, ExtraService
from .pricing import build_quote
from .serializers import (
    AdminBookingDetailSerializer, AdminBookingListSerializer, BookingCreateSerializer, ExtraServiceAdminSerializer,
    GuestBookingSerializer, ModifyBookingSerializer, NoteSerializer, QuoteSerializer, StatusActionSerializer,
    booking_options,
)
from .tokens import resolve_booking
from .whatsapp import guest_to_owner_url
from .vehicle_data import quote_vehicle


def guest_booking_or_404(request) -> Booking:
    """Authorise a guest by booking reference + secret token (headers preferred)."""
    ref = request.headers.get("X-Booking-Reference") or request.query_params.get("reference") or \
        (request.data.get("reference") if hasattr(request, "data") and hasattr(request.data, "get") else None)
    token = request.headers.get("X-Booking-Token") or \
        (request.data.get("token") if hasattr(request, "data") and hasattr(request.data, "get") else None)
    booking = resolve_booking(ref, token)
    if booking is None:
        # Same response whether the reference exists or not (no enumeration).
        raise NotFound("We could not find a booking for that link. It may have expired — contact us for a new one.")
    return booking


# --------------------------------------------------------------------------
# Public
# --------------------------------------------------------------------------
class BookingOptionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(booking_options())


class QuoteView(APIView):
    """Live price estimate. Same engine that prices the real booking."""

    permission_classes = [AllowAny]
    throttle_classes = [QuoteThrottle]

    def post(self, request):
        s = QuoteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        pickup_at = services.combine(d["pickup_date"], d["pickup_time"])
        return_at = services.combine(d["return_date"], d["return_time"])
        services.validate_rental_window(pickup_at, return_at)
        quote = build_quote(vehicle=quote_vehicle(d["vehicle_snapshot"]), pickup_at=pickup_at, return_at=return_at,
                            pickup_type=d["pickup_type"], return_type=d["return_type"], extras=d.get("extras"))
        return Response(quote.as_dict())


class BookingCreateView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [BookingCreateThrottle]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        s = BookingCreateSerializer.from_request(request)
        s.is_valid(raise_exception=True)
        if (request.FILES and not settings.DEBUG
                and not getattr(settings, "PRIVATE_DOCUMENTS_DURABLE", False)):
            raise ValidationError({
                "documents": "Secure durable document storage is not configured. Please contact us to arrange this booking."
            })
        documents = {}
        if request.FILES.get("passport"):
            documents[DocumentType.PASSPORT] = request.FILES["passport"]
        if request.FILES.get("driving_licence"):
            documents[DocumentType.DRIVING_LICENCE] = request.FILES["driving_licence"]
        result = services.create_booking(dict(s.validated_data), documents=documents, request=request)
        b, inv = result.booking, result.invoice
        # The booking is already committed before voucher rendering starts.
        # If PDF generation fails, keep the saved booking and let the guest
        # retry through the protected confirmation-download endpoint.
        voucher_available = False
        try:
            from .vouchers import ensure_voucher

            ensure_voucher(b)
            voucher_available = True
        except Exception:
            logging.getLogger(__name__).exception(
                "Guest voucher generation failed for saved booking %s", b.booking_reference
            )
        response = Response({
            "booking_reference": b.booking_reference,
            "access_token": result.access_token,
            "invoice_number": inv.invoice_number,
            "booking_status": b.booking_status,
            "booking_status_display": b.get_booking_status_display(),
            "payment_status": b.payment_status,
            "payment_status_display": b.get_payment_status_display(),
            "payment_method": b.payment_method,
            "payment_method_display": b.get_payment_method_display(),
            "grand_total": str(b.grand_total),
            "currency": b.currency,
            "hold_expires_at": b.hold_expires_at,
            "whatsapp_url": guest_to_owner_url(b),
            "voucher_available": voucher_available,
            "voucher_download_url": "/api/v1/bookings/confirmation/download/",
        }, status=status.HTTP_201_CREATED)
        response["Cache-Control"] = "private, no-store, max-age=0"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class BookingTrackView(APIView):
    """Guest booking lookup. Requires reference + token (sent as headers)."""

    permission_classes = [AllowAny]
    throttle_classes = [BookingAccessThrottle]

    def get(self, request):
        b = guest_booking_or_404(request)
        data = GuestBookingSerializer(b, context={"request": request}).data
        data["whatsapp_url"] = guest_to_owner_url(b)
        data["payment_options"] = booking_options()["payment_methods"]
        return Response(data)


class GuestBookingConfirmationDownloadView(APIView):
    """Generate a private PDF only after validating the guest's booking token."""

    permission_classes = [AllowAny]
    throttle_classes = [BookingAccessThrottle]

    def get(self, request):
        booking = guest_booking_or_404(request)
        from .vouchers import ensure_voucher

        voucher = ensure_voucher(booking)
        as_attachment = request.query_params.get("inline") != "1"
        response = private_file_response(
            voucher, f"Rafiki-Booking-{booking.booking_reference}.pdf", as_attachment=as_attachment,
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response


# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------
class AdminBookingFilter(django_filters.FilterSet):
    booking_status = django_filters.MultipleChoiceFilter(choices=BookingStatus.choices)
    payment_status = django_filters.CharFilter()
    vehicle = django_filters.UUIDFilter(field_name="vehicle_id")
    customer = django_filters.UUIDFilter(field_name="customer_id")
    pickup_from = django_filters.DateFilter(field_name="pickup_date", lookup_expr="gte")
    pickup_to = django_filters.DateFilter(field_name="pickup_date", lookup_expr="lte")
    created_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    outstanding = django_filters.BooleanFilter(method="filter_outstanding")

    class Meta:
        model = Booking
        fields = ["booking_status", "payment_status", "payment_method"]

    def filter_outstanding(self, qs, name, value):
        from django.db.models import F
        if value:
            return qs.filter(amount_paid__lt=F("grand_total")).exclude(
                booking_status__in=[BookingStatus.REJECTED, BookingStatus.CANCELLED, BookingStatus.EXPIRED])
        return qs


class AdminBookingViewSet(viewsets.ReadOnlyModelViewSet):
    filterset_class = AdminBookingFilter
    ordering_fields = ["created_at", "pickup_date", "grand_total", "booking_reference"]
    ordering = ["-created_at"]
    action_roles = {"modify": FINANCE_ROLES, "document_download": FINANCE_ROLES, "document_verify": FINANCE_ROLES,
                    "dossier": FINANCE_ROLES}

    def get_queryset(self):
        qs = Booking.objects.select_related("customer", "vehicle").prefetch_related("extras", "vehicle__images")
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(booking_reference__icontains=q) | Q(customer__full_name__icontains=q)
                           | Q(customer__email__icontains=q) | Q(customer__phone__icontains=q)
                           | Q(invoices__invoice_number__icontains=q)).distinct()
        return qs

    def get_serializer_class(self):
        return AdminBookingDetailSerializer if self.action != "list" else AdminBookingListSerializer

    def _transition(self, request, new_status):
        booking = self.get_object()
        s = StatusActionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if new_status in (BookingStatus.REJECTED, BookingStatus.CANCELLED) and not s.validated_data["notes"].strip():
            return Response({"error": {"code": "validation_error", "message": "Please give a reason."}},
                            status=status.HTTP_400_BAD_REQUEST)
        services.change_status(booking, new_status, actor=request.user, notes=s.validated_data["notes"],
                               request=request, notify_guest=s.validated_data["notify_guest"])
        return Response(AdminBookingDetailSerializer(self.get_queryset().get(pk=booking.pk),
                                                     context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._transition(request, BookingStatus.CONFIRMED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._transition(request, BookingStatus.REJECTED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._transition(request, BookingStatus.CANCELLED)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._transition(request, BookingStatus.COMPLETED)

    @action(detail=True, methods=["post"])
    def notes(self, request, pk=None):
        booking = self.get_object()
        s = NoteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        note = BookingNote.objects.create(booking=booking, author=request.user, body=s.validated_data["body"])
        return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def modify(self, request, pk=None):
        booking = self.get_object()
        s = ModifyBookingSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        changes = dict(s.validated_data)
        reason = changes.pop("reason")
        _, invoice = services.modify_booking(booking, changes, actor=request.user, reason=reason, request=request)
        data = AdminBookingDetailSerializer(self.get_queryset().get(pk=booking.pk), context={"request": request}).data
        data["revised_invoice"] = invoice.invoice_number if invoice else None
        return Response(data)

    @action(detail=True, methods=["get"], url_path=r"documents/(?P<doc_id>[0-9a-f-]+)/download")
    def document_download(self, request, pk=None, doc_id=None):
        booking = self.get_object()
        doc = get_object_or_404(BookingDocument, pk=doc_id, booking=booking)
        if not doc.secure_file:
            raise NotFound("This document has been deleted under the data-retention policy.")
        audit("document.viewed", actor=request.user, target=doc, request=request,
              summary=f"{doc.get_document_type_display()} for {booking.booking_reference}")
        name = f"{booking.booking_reference}-{doc.document_type.lower()}.{doc.file_kind or 'bin'}"
        return private_file_response(doc.secure_file, name, as_attachment=request.query_params.get("inline") != "1")

    @action(detail=True, methods=["get"])
    def dossier(self, request, pk=None):
        booking = self.get_object()
        from .dossier import ensure_dossier

        try:
            dossier = ensure_dossier(booking, actor=request.user, request=request)
        except Exception as exc:
            raise BusinessRuleError("The private booking dossier could not be generated.") from exc
        audit("dossier.downloaded", actor=request.user, target=booking, request=request,
              summary=f"Private booking dossier downloaded for {booking.booking_reference}")
        return private_file_response(dossier.pdf_file,
                                     f"Rafiki-Internal-Dossier-{booking.booking_reference}.pdf")

    @action(detail=True, methods=["post"], url_path=r"documents/(?P<doc_id>[0-9a-f-]+)/verify")
    def document_verify(self, request, pk=None, doc_id=None):
        booking = self.get_object()
        doc = get_object_or_404(BookingDocument, pk=doc_id, booking=booking)
        new = request.data.get("status")
        if new not in (DocumentStatus.VERIFIED, DocumentStatus.REJECTED) or doc.verification_status == DocumentStatus.PURGED:
            return Response({"error": {"code": "validation_error", "message": "Invalid document status."}},
                            status=status.HTTP_400_BAD_REQUEST)
        doc.verification_status, doc.verified_by, doc.verified_at = new, request.user, timezone.now()
        doc.save()
        audit("document.reviewed", actor=request.user, target=doc, request=request, summary=new)
        return Response({"id": str(doc.pk), "verification_status": doc.verification_status})


class AdminExtraServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ExtraServiceAdminSerializer
    queryset = ExtraService.objects.all()
    pagination_class = None
    action_roles = {"create": FINANCE_ROLES, "update": FINANCE_ROLES, "partial_update": FINANCE_ROLES,
                    "destroy": FINANCE_ROLES, "list": ALL_ROLES, "retrieve": ALL_ROLES}

    def perform_update(self, serializer):
        before = str(serializer.instance.price)
        obj = serializer.save()
        audit("extra_service.updated", actor=self.request.user, target=obj, request=self.request,
              summary=f"{obj.name}: ${before} → ${obj.price}")

    def perform_destroy(self, instance):
        if instance.is_system:
            from apps.core.exceptions import BusinessRuleError
            raise BusinessRuleError("Core services cannot be deleted — deactivate them instead.")
        instance.delete()
