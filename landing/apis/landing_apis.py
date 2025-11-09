from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer

# Cache duration in seconds
CACHE_TTL = 60

@method_decorator(cache_page(CACHE_TTL), name='dispatch')
class LandingPageView(APIView):
    """
    Landing page endpoint:
    - Renders 'landing.html' for browsers
    - Returns JSON for API clients
    - Cached for 60 seconds
    """
    permission_classes = [AllowAny]
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]  # HTML + JSON

    template_name = "landing.html"

    def get(self, request, format=None):
        context = {
            "media_url": getattr(settings, "MEDIA_URL", "/media/"),
            "minio_enabled": getattr(settings, "USE_MINIO", False),
        }

        return Response(context)
