from django.contrib import admin
from django.urls import path

from shona_api.health.views import HealthView
from shona_api.figurative_language.views import TsumoDetailView, TsumoListView
from shona_api.lexicon.views import LemmaReadView, SearchView
from shona_api.morphology.views import AnalyzeView, GenerateView
from shona_api.web.views import DictionarySearchView


urlpatterns = [
    path("", DictionarySearchView.as_view(), name="dictionary-search"),
    path("admin/", admin.site.urls),
    path("dictionary/", DictionarySearchView.as_view(), name="dictionary-search-alias"),
    path("v1/analyze", AnalyzeView.as_view(), name="analyze"),
    path(
        "v1/figurative-expressions/tsumo",
        TsumoListView.as_view(),
        name="tsumo-list",
    ),
    path(
        "v1/figurative-expressions/tsumo/<str:public_id>",
        TsumoDetailView.as_view(),
        name="tsumo-detail",
    ),
    path("v1/generate", GenerateView.as_view(), name="generate"),
    path("v1/lemmas/<str:public_id>", LemmaReadView.as_view(), name="lemma-read"),
    path("v1/search", SearchView.as_view(), name="search"),
    path("health", HealthView.as_view(), name="health"),
    path("health/", HealthView.as_view(), name="health-slash"),
]
