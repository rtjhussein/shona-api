from django.contrib import admin
from django.urls import path

from shona_api.health.views import HealthView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", HealthView.as_view(), name="health"),
    path("health/", HealthView.as_view(), name="health-slash"),
]
