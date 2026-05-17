from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse
from django.views.generic import TemplateView

from .progress import build_data_progress_snapshot


class DictionarySearchView(TemplateView):
    template_name = "web/dictionary_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_endpoint"] = reverse("search")
        context["entry_url_template"] = reverse(
            "dictionary-entry",
            kwargs={"public_id": "__PUBLIC_ID__"},
        )
        return context


class DictionaryEntryView(TemplateView):
    template_name = "web/dictionary_entry.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        public_id = self.kwargs["public_id"]
        context["lemma_public_id"] = public_id
        context["lemma_endpoint"] = reverse(
            "lemma-read",
            kwargs={"public_id": public_id},
        )
        context["search_url"] = reverse("dictionary-search")
        context["tsumo_endpoint"] = reverse("tsumo-list")
        context["madimikira_endpoint"] = reverse("madimikira-list")
        return context


class DataProgressView(UserPassesTestMixin, TemplateView):
    template_name = "web/data_progress.html"
    login_url = "/admin/login/"

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["snapshot"] = build_data_progress_snapshot()
        return context
