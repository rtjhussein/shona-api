from pathlib import Path

from django.test import Client
from django.urls import reverse


SEARCH_JS = Path("shona_api/web/static/web/dictionary-search.js")
SEARCH_CSS = Path("shona_api/web/static/web/dictionary-search.css")
ENTRY_JS = Path("shona_api/web/static/web/dictionary-entry.js")


def test_dictionary_search_page_loads_without_api_auth():
    response = Client().get(reverse("dictionary-search"))

    assert response.status_code == 200
    assert b"Shona Dictionary" in response.content
    assert b'data-search-endpoint="/v1/search"' in response.content
    assert b'data-entry-url-template="/dictionary/entries/__PUBLIC_ID__/"' in (
        response.content
    )
    assert b"data-filter-headword-kind" in response.content
    assert b"data-filter-dialect" in response.content


def test_dictionary_search_alias_route_loads_same_public_ui():
    response = Client().get("/dictionary/")

    assert response.status_code == 200
    assert b"Shona Dictionary" in response.content
    assert b"dictionary-search.js" in response.content


def test_dictionary_entry_page_loads_without_api_auth():
    response = Client().get(
        reverse("dictionary-entry", kwargs={"public_id": "lemma_demo"})
    )

    assert response.status_code == 200
    assert b"Shona Dictionary" in response.content
    assert b'data-lemma-public-id="lemma_demo"' in response.content
    assert b'data-lemma-endpoint="/v1/lemmas/lemma_demo"' in response.content
    assert b'data-entry-url-template="/dictionary/entries/__PUBLIC_ID__/"' in (
        response.content
    )
    assert b'data-tsumo-endpoint="/v1/figurative-expressions/tsumo"' in (
        response.content
    )
    assert b'data-madimikira-endpoint="/v1/figurative-expressions/madimikira"' in (
        response.content
    )
    assert b"dictionary-entry.js" in response.content


def test_dictionary_search_javascript_renders_infinitive_morphology_slots():
    js_content = SEARCH_JS.read_text(encoding="utf-8")
    css_content = SEARCH_CSS.read_text(encoding="utf-8")

    assert "infinitive_prefix" in js_content
    assert "slot-pill--infinitive" in css_content


def test_dictionary_search_javascript_renders_unsupported_future_lanes():
    js_content = SEARCH_JS.read_text(encoding="utf-8")
    css_content = SEARCH_CSS.read_text(encoding="utf-8")

    assert "future_lanes" in js_content
    assert "unsupported-lane-list" in css_content


def test_dictionary_web_renders_derived_form_evidence():
    search_js = SEARCH_JS.read_text(encoding="utf-8")
    entry_js = ENTRY_JS.read_text(encoding="utf-8")
    css_content = SEARCH_CSS.read_text(encoding="utf-8")

    assert "derived_form_evidence" in search_js
    assert "derived_form_evidence" in entry_js
    assert "derived-evidence" in css_content


def test_dictionary_web_renders_standardized_example_pairs():
    search_js = SEARCH_JS.read_text(encoding="utf-8")
    entry_js = ENTRY_JS.read_text(encoding="utf-8")
    css_content = SEARCH_CSS.read_text(encoding="utf-8")

    assert "exampleTextPart" in search_js
    assert "exampleTextPart" in entry_js
    assert "example-shona" in css_content
    assert "example-english" in css_content


def test_dictionary_web_renders_cross_reference_links():
    search_js = SEARCH_JS.read_text(encoding="utf-8")
    entry_js = ENTRY_JS.read_text(encoding="utf-8")
    css_content = SEARCH_CSS.read_text(encoding="utf-8")

    assert "target_public_id" in search_js
    assert "target_public_id" in entry_js
    assert "xref-link" in css_content
    assert "xref-unresolved" in css_content


def test_dictionary_web_renders_entry_quality_chips():
    search_js = SEARCH_JS.read_text(encoding="utf-8")
    entry_js = ENTRY_JS.read_text(encoding="utf-8")

    assert "entry_quality" in search_js
    assert "entry_quality" in entry_js
    assert "renderEntryQualityChips" in search_js
    assert "renderEntryQualityChips" in entry_js


def test_dictionary_web_submits_compact_search_filters():
    search_js = SEARCH_JS.read_text(encoding="utf-8")
    css_content = SEARCH_CSS.read_text(encoding="utf-8")

    assert "appendSearchFilters" in search_js
    assert "headword_kind" in search_js
    assert "filter-row" in css_content
