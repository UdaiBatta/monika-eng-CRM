import hashlib

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.db.models import Q
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, Throttled, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.rbac.services import effective_permission_codes

from .models import User
from .serializers import ChangePasswordSerializer, LoginSerializer, UserSerializer


def _login_cache_key(request, identifier):
    ip = request.META.get("REMOTE_ADDR", "unknown")
    digest = hashlib.sha256(f"{ip}:{identifier.lower()}".encode()).hexdigest()
    return f"login-failures:{digest}"


class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class LoginView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(csrf_protect)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"]
        key = _login_cache_key(request, identifier)
        failures = cache.get(key, 0)
        if failures >= settings.LOGIN_FAILURE_LIMIT:
            raise Throttled(wait=settings.LOGIN_FAILURE_WINDOW_SECONDS)

        account = User.objects.filter(Q(email__iexact=identifier) | Q(username__iexact=identifier)).first()
        user = authenticate(
            request,
            username=account.email if account else identifier,
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            cache.set(key, failures + 1, timeout=settings.LOGIN_FAILURE_WINDOW_SECONDS)
            raise AuthenticationFailed("Invalid sign-in details.")
        cache.delete(key)
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = UserSerializer(request.user).data
        employee = getattr(request.user, "employee", None)
        data["employee"] = (
            None
            if employee is None
            else {
                "id": employee.id,
                "employee_code": employee.employee_code,
                "display_name": employee.display_name,
                "company_id": employee.company_id,
                "branch_id": employee.branch_id,
                "department_id": employee.department_id,
                "designation_id": employee.designation_id,
            }
        )
        data["permissions"] = effective_permission_codes(request.user)
        return Response(data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data["current_password"]):
            raise ValidationError({"current_password": ["Current password is incorrect."]})
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("email")
    serializer_class = UserSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "accounts.user.view",
        "retrieve": "accounts.user.view",
        "create": "accounts.user.manage",
        "update": "accounts.user.manage",
        "partial_update": "accounts.user.manage",
        "destroy": "accounts.user.manage",
        "activate": "accounts.user.manage",
        "deactivate": "accounts.user.manage",
    }
    search_fields = ["email", "username", "first_name", "last_name"]
    ordering_fields = ["email", "date_joined", "last_login"]

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response(self.get_serializer(user).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            raise ValidationError("You cannot deactivate your own account.")
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(self.get_serializer(user).data)
