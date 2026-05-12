from django.urls import reverse
from django.views.generic import TemplateView


class DictionarySearchView(TemplateView):
    template_name = "web/dictionary_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_endpoint"] = reverse("search")
        return context
