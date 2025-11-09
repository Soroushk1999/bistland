from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from rest_framework import status

from landing.serializers import SubmitPhoneSerializer


class SubmitPhoneSchema:
    """Schema for the Submit Phone API (Lead Capture)"""

    post = extend_schema(
        summary="Submit a phone number for lead registration",
        description=(
            "Accepts a phone number and queues it for lead processing. "
            "If the phone number has already been submitted within the past 24 hours, "
            "a duplicate response will be returned instead."
        ),
        request=SubmitPhoneSerializer,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                response=SubmitPhoneSerializer,
                description="The phone number has already been submitted within the last 24 hours.",
                examples=[
                    OpenApiExample(
                        "Duplicate",
                        value={
                            "ok": True,
                            "duplicate": True,
                        },
                    )
                ],
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=SubmitPhoneSerializer,
                description="Invalid or incorrectly formatted phone number.",
                examples=[
                    OpenApiExample(
                        "Invalid phone",
                        value={
                            "ok": False,
                            "error": "invalid_phone",
                        },
                    )
                ],
            ),
            status.HTTP_429_TOO_MANY_REQUESTS: OpenApiResponse(
                response=SubmitPhoneSerializer,
                description="Too many requests from this IP (rate limit exceeded).",
                examples=[
                    OpenApiExample(
                        "Too many requests",
                        value={
                            "ok": False,
                            "error": "too_many_requests",
                        },
                    )
                ],
            ),
        },
        tags=["Leads"],
        operation_id="submitPhone",
    )
