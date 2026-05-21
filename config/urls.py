from django.contrib import admin
from django.urls import path

from shona_api.api_docs.views import OpenAPISpecView
from shona_api.health.views import HealthView
from shona_api.figurative_language.views import (
    MadimikiraDetailView,
    MadimikiraListView,
    TsumoDetailView,
    TsumoListView,
)
from shona_api.lexicon.views import LemmaReadView, SearchView
from shona_api.morphology.views import AnalyzeView, GenerateView
from shona_api.web.views import (
    CreateLocalAPIKeyView,
    DataProgressView,
    DictionaryEntryView,
    DictionarySearchView,
    IngestionDashboardView,
    IngestionRunStatusView,
    SaveGeminiKeyView,
    StartIngestionRunView,
)


urlpatterns = [
    path("", DictionarySearchView.as_view(), name="dictionary-search"),
    path("admin/", admin.site.urls),
    path("dictionary/", DictionarySearchView.as_view(), name="dictionary-search-alias"),
    path("data-progress/", DataProgressView.as_view(), name="data-progress"),
    path(
        "data-progress/ingestion/",
        IngestionDashboardView.as_view(),
        name="ingestion-dashboard",
    ),
    path(
        "data-progress/ingestion/gemini-key/",
        SaveGeminiKeyView.as_view(),
        name="ingestion-gemini-key-save",
    ),
    path(
        "data-progress/ingestion/runs/start/",
        StartIngestionRunView.as_view(),
        name="ingestion-run-start",
    ),
    path(
        "data-progress/ingestion/runs/<int:pk>/",
        IngestionRunStatusView.as_view(),
        name="ingestion-run-status",
    ),
    path(
        "data-progress/local-api-key/",
        CreateLocalAPIKeyView.as_view(),
        name="local-api-key-create",
    ),
    path("openapi.json", OpenAPISpecView.as_view(), name="openapi-spec"),
    path(
        "dictionary/entries/<str:public_id>/",
        DictionaryEntryView.as_view(),
        name="dictionary-entry",
    ),
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
    path(
        "v1/figurative-expressions/madimikira",
        MadimikiraListView.as_view(),
        name="madimikira-list",
    ),
    path(
        "v1/figurative-expressions/madimikira/<str:public_id>",
        MadimikiraDetailView.as_view(),
        name="madimikira-detail",
    ),
    path("v1/generate", GenerateView.as_view(), name="generate"),
    path("v1/lemmas/<str:public_id>", LemmaReadView.as_view(), name="lemma-read"),
    path("v1/search", SearchView.as_view(), name="search"),
    path("health", HealthView.as_view(), name="health"),
    path("health/", HealthView.as_view(), name="health-slash"),
]
