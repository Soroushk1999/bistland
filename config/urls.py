from django.contrib import admin
from django.urls import include, path
from django.views.decorators.cache import cache_page
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


class HealthzView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, _request):
        return Response({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", HealthzView.as_view(), name="healthz"),
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/swagger",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("", include("django_prometheus.urls"), name="metrics"),
    path("", include("landing.urls"), name="landing"),
]


