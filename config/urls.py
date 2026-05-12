from django.contrib import admin
from django.urls import path

from shona_api.health.views import HealthView
from shona_api.lexicon.views import LemmaReadView, SearchView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("v1/lemmas/<str:public_id>", LemmaReadView.as_view(), name="lemma-read"),
    path("v1/search", SearchView.as_view(), name="search"),
    path("health", HealthView.as_view(), name="health"),
    path("health/", HealthView.as_view(), name="health-slash"),
]
