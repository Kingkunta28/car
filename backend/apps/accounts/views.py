from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.throttles import LoginThrottle
from apps.core.utils import audit

from .models import AdminUser


class AdminUserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = AdminUser
        fields = ["id", "email", "full_name", "role", "role_display", "is_superuser"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, max_length=128)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        email = s.validated_data["email"].lower()
        user = authenticate(request, username=email, password=s.validated_data["password"])
        if user is None or not user.dashboard_access:
            audit("auth.login_failed", summary=f"Failed sign-in for {email}", request=request)
            return Response(
                {"error": {"code": "invalid_credentials", "message": "Invalid email or password."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        login(request, user)
        audit("auth.login", actor=user, target=user, summary="Signed in", request=request)
        return Response({"user": AdminUserSerializer(user).data, "csrfToken": get_token(request)})


class LogoutView(APIView):
    def post(self, request):
        audit("auth.logout", actor=request.user, target=request.user, summary="Signed out", request=request)
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response({"user": AdminUserSerializer(request.user).data})
