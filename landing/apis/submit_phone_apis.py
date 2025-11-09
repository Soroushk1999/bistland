import time
import logging

from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema_view

from landing.tasks import save_phone_in_sql_task, log_request_in_mongo_task
from landing.serializers import SubmitPhoneSerializer
from landing.schemas.submit_phone_schemas import SubmitPhoneSchema
from landing.utils import get_client_ip
from landing.throttles import SubmitPerIPThrottle  
from landing.metrics import endpoint_latency, endpoint_requests


logger = logging.getLogger(__name__)


@extend_schema_view(
    post=SubmitPhoneSchema.post
)
class SubmitPhoneView(APIView):
    """
    API endpoint for submitting phone numbers.
    Handles deduplication, asynchronous persistence,
    request logging, and Prometheus metrics.
    """
    # throttle_classes = [SubmitPerIPThrottle]  # enable if rate-limiting is needed
    serializer_class = SubmitPhoneSerializer

    def post(self, request):
        start_time = time.perf_counter()
        ip = get_client_ip(request) or "unknown"
        
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            phone = serializer.validated_data["phone"]

            logger.info(f"📨 Received phone submission: {phone} from IP {ip}")

            # --- Deduplication logic ---
            dedup_key = f"dedup:phone:{phone}"
            is_new_submission = cache.add(dedup_key, "1", timeout=24 * 3600)

            # Log every request asynchronously in mongodb
            log_request_in_mongo_task.delay({
                "phone": phone,
                "path": request.path,
                "ip": ip,
                "ua": request.META.get("HTTP_USER_AGENT", ""),
                "duplicate": not is_new_submission,
            })

            # --- Handle duplicate ---
            if not is_new_submission:
                logger.info(f"⚠️ Duplicate phone detected: {phone}")
                return Response({"ok": True, "duplicate": True}, status=status.HTTP_200_OK)

            # --- save on postgresql ---
            save_phone_in_sql_task.delay(phone=phone)    
            logger.info(f"✅ Phone submission queued successfully: {phone}")
            endpoint_requests.labels(status="success").inc()
            
            return Response(
                {"ok": True, "queued": True, "duplicate": False},
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.exception(f"❌ Error processing phone submission: {e}")
            endpoint_requests.labels(status="error").inc()
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        finally:
            duration = time.perf_counter() - start_time
            endpoint_latency.observe(duration)
            logger.info(f"⏱️ SubmitPhoneView duration: {duration:.3f}s (IP: {ip})")


        
