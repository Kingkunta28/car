"""Consistent API error envelope:

    {"error": {"code": "validation_error", "message": "...", "details": {...}}}
"""
import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class BusinessRuleError(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "business_rule"
    default_detail = "The request breaks a business rule."


class ConflictError(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"
    default_detail = "The request conflicts with the current state."


def _first_message(detail):
    if isinstance(detail, list) and detail:
        return _first_message(detail[0])
    if isinstance(detail, dict) and detail:
        key, value = next(iter(detail.items()))
        msg = _first_message(value)
        return msg if key in ("non_field_errors", "detail") else f"{key.replace('_', ' ').capitalize()}: {msg}"
    return str(detail)


def api_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(exc.message_dict if hasattr(exc, "error_dict") else exc.messages)
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
        return Response(
            {"error": {"code": "server_error", "message": "An unexpected error occurred. Please try again."}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    detail = response.data
    if isinstance(exc, exceptions.ValidationError):
        code, message = "validation_error", _first_message(detail)
        details = detail
    else:
        codes = exc.get_codes() if hasattr(exc, "get_codes") else "error"
        code = codes if isinstance(codes, str) else "error"
        message = detail.get("detail", _first_message(detail)) if isinstance(detail, dict) else _first_message(detail)
        details = None
    body = {"error": {"code": code, "message": str(message)}}
    if details is not None:
        body["error"]["details"] = details
    response.data = body
    return response
