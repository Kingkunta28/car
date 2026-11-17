from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts import views as auth_views
from apps.bookings import views as booking_views
from apps.core import views as core_views
from apps.customers.views import AdminCustomerViewSet
from apps.invoices import views as invoice_views
from apps.notifications.views import AdminNotificationViewSet
from apps.payments import views as payment_views
from apps.reports import views as report_views
from apps.vehicles.views import AdminVehicleViewSet, PublicVehicleViewSet

public = DefaultRouter(trailing_slash=True)
public.include_root_view = False
public.register("vehicles", PublicVehicleViewSet, basename="vehicle")

staff = DefaultRouter(trailing_slash=True)
staff.include_root_view = False
staff.register("bookings", booking_views.AdminBookingViewSet, basename="admin-booking")
staff.register("vehicles", AdminVehicleViewSet, basename="admin-vehicle")
staff.register("extras", booking_views.AdminExtraServiceViewSet, basename="admin-extra")
staff.register("customers", AdminCustomerViewSet, basename="admin-customer")
staff.register("invoices", invoice_views.AdminInvoiceViewSet, basename="admin-invoice")
staff.register("receipts", invoice_views.AdminReceiptViewSet, basename="admin-receipt")
staff.register("payments", payment_views.AdminPaymentViewSet, basename="admin-payment")
staff.register("notifications", AdminNotificationViewSet, basename="admin-notification")
staff.register("testimonials", core_views.AdminTestimonialViewSet, basename="admin-testimonial")
staff.register("messages", core_views.AdminContactMessageViewSet, basename="admin-message")
staff.register("audit-logs", core_views.AuditLogViewSet, basename="admin-audit")

admin_api = [
    path("auth/csrf/", auth_views.CsrfView.as_view()),
    path("auth/login/", auth_views.LoginView.as_view()),
    path("auth/logout/", auth_views.LogoutView.as_view()),
    path("auth/me/", auth_views.MeView.as_view()),
    path("dashboard/", report_views.DashboardView.as_view()),
    path("reports/<slug:kind>/", report_views.ReportView.as_view()),
    path("settings/", core_views.AdminSettingsView.as_view()),
    path("", include(staff.urls)),
]

api_v1 = [
    path("health/", core_views.HealthView.as_view()),
    path("site/", core_views.SiteView.as_view()),
    path("testimonials/", core_views.PublicTestimonialsView.as_view()),
    path("contact/", core_views.ContactView.as_view()),
    path("booking-options/", booking_views.BookingOptionsView.as_view()),
    path("bookings/quote/", booking_views.QuoteView.as_view()),
    path("bookings/track/", booking_views.BookingTrackView.as_view()),
    path("bookings/", booking_views.BookingCreateView.as_view()),
    path("invoices/download/", invoice_views.GuestInvoiceDownloadView.as_view()),
    path("receipts/download/", invoice_views.GuestReceiptDownloadView.as_view()),
    path("payments/manual/", payment_views.ManualPaymentView.as_view()),
    path("payments/online/initiate/", payment_views.OnlinePaymentInitiateView.as_view()),
    path("payments/online/verify/", payment_views.OnlinePaymentVerifyView.as_view()),
    path("webhooks/payments/<slug:provider>/", payment_views.PaymentWebhookView.as_view()),
    path("admin/", include(admin_api)),
    path("", include(public.urls)),
]

urlpatterns = [
    path(settings.DJANGO_ADMIN_URL, admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("sitemap.xml", core_views.sitemap_xml),
]

# Public media (vehicle photos, logo) in development. Private files are never routed.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Rafiki Car Hire — system administration"
admin.site.site_title = "Rafiki Car Hire"
