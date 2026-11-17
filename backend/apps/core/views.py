from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import ADMIN_ONLY, ALL_ROLES
from apps.core.files import IMAGE_TYPES, validate_upload
from apps.core.throttles import ContactThrottle

from .models import AuditLog, ContactMessage, SiteSettings, Testimonial
from .utils import audit


class PublicSiteSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = ["business_name", "tagline", "business_email", "business_phone", "whatsapp_number",
                  "business_address", "logo_url", "hero_image_url", "currency"]

    def _url(self, f):
        return f.url if f else None

    def get_logo_url(self, obj):
        return self._url(obj.logo)

    def get_hero_image_url(self, obj):
        return self._url(obj.hero_image)


class AdminSiteSerializer(PublicSiteSerializer):
    logo = serializers.ImageField(required=False, allow_null=True, write_only=True)
    hero_image = serializers.ImageField(required=False, allow_null=True, write_only=True)

    class Meta(PublicSiteSerializer.Meta):
        fields = PublicSiteSerializer.Meta.fields + [
            "logo", "hero_image", "owner_notification_email", "invoice_footer", "invoice_terms", "payment_instructions",
            "tax_rate", "tax_label", "email_configuration_reference", "updated_at",
        ]
        read_only_fields = ["currency", "updated_at"]

    def validate_logo(self, f):
        if f:
            validate_upload(f, allowed=IMAGE_TYPES, max_mb=4)
        return f

    def validate_hero_image(self, f):
        if f:
            validate_upload(f, allowed=IMAGE_TYPES, max_mb=10)
        return f


class SiteView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(PublicSiteSerializer(SiteSettings.load(), context={"request": request}).data)


class AdminSettingsView(APIView):
    required_roles = ALL_ROLES

    def get(self, request):
        return Response(AdminSiteSerializer(SiteSettings.load(), context={"request": request}).data)

    def patch(self, request):
        if not request.user.has_role(*ADMIN_ONLY):
            return Response({"error": {"code": "permission_denied", "message": "Only administrators can change settings."}},
                            status=status.HTTP_403_FORBIDDEN)
        site = SiteSettings.load()
        s = AdminSiteSerializer(site, data=request.data, partial=True, context={"request": request})
        s.is_valid(raise_exception=True)
        s.save()
        audit("settings.updated", actor=request.user, target=site, request=request,
              summary="Site settings updated", fields=sorted(k for k in request.data.keys() if k != "logo"))
        return Response(AdminSiteSerializer(site, context={"request": request}).data)


class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = ["id", "customer_name", "country", "quote", "rating", "is_published", "display_order", "created_at"]
        read_only_fields = ["id", "created_at"]


class PublicTestimonialsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Testimonial.objects.filter(is_published=True)[:12]
        return Response([{k: v for k, v in TestimonialSerializer(t).data.items()
                          if k in ("id", "customer_name", "country", "quote", "rating")} for t in qs])


class AdminTestimonialViewSet(viewsets.ModelViewSet):
    serializer_class = TestimonialSerializer
    queryset = Testimonial.objects.all()
    pagination_class = None


class ContactSerializer(serializers.ModelSerializer):
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)  # honeypot

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "subject", "message", "website"]


class ContactView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ContactThrottle]

    def post(self, request):
        s = ContactSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if s.validated_data.pop("website", ""):
            return Response({"received": True}, status=status.HTTP_201_CREATED)  # silently drop bots
        from apps.notifications import services as notify

        msg = s.save()
        notify.contact_message(msg)
        return Response({"received": True}, status=status.HTTP_201_CREATED)


class AdminContactMessageViewSet(viewsets.ModelViewSet):
    class _S(serializers.ModelSerializer):
        class Meta:
            model = ContactMessage
            fields = ["id", "name", "email", "phone", "subject", "message", "is_handled", "created_at"]
            read_only_fields = ["id", "name", "email", "phone", "subject", "message", "created_at"]

    serializer_class = _S
    queryset = ContactMessage.objects.all()
    http_method_names = ["get", "patch", "head", "options"]
    filterset_fields = ["is_handled"]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    required_roles = ADMIN_ONLY

    class _S(serializers.ModelSerializer):
        actor = serializers.CharField(source="actor.full_name", default=None)

        class Meta:
            model = AuditLog
            fields = ["id", "actor", "action", "target_type", "target_id", "summary", "metadata", "ip_address",
                      "created_at"]

    serializer_class = _S
    queryset = AuditLog.objects.select_related("actor")
    filterset_fields = ["action", "target_type", "target_id"]
    search_fields = ["summary", "action"]


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        try:
            with connection.cursor() as c:
                c.execute("SELECT 1")
            db = "ok"
        except Exception:
            db = "error"
        code = 200 if db == "ok" else 503
        return Response({"status": "ok" if db == "ok" else "degraded", "database": db,
                         "time": timezone.now().isoformat()}, status=code)


def sitemap_xml(request):
    from apps.vehicles.models import Vehicle

    base = settings.FRONTEND_URL
    pages = ["", "/fleet", "/about", "/before-you-rent", "/contact", "/book", "/privacy", "/terms"]
    urls = [(f"{base}{p}", None, "1.0" if p == "" else "0.7") for p in pages]
    for slug, updated in Vehicle.objects.filter(is_active=True).values_list("slug", "updated_at"):
        urls.append((f"{base}/fleet/{slug}", updated, "0.8"))
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod, prio in urls:
        body.append(f"<url><loc>{loc}</loc>{f'<lastmod>{lastmod:%Y-%m-%d}</lastmod>' if lastmod else ''}"
                    f"<priority>{prio}</priority></url>")
    body.append("</urlset>")
    return HttpResponse("\n".join(body), content_type="application/xml")
