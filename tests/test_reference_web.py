from django.test import Client
from django.urls import reverse


def test_dictionary_search_page_loads_without_api_auth():
    response = Client().get(reverse("dictionary-search"))

    assert response.status_code == 200
    assert b"Shona Dictionary" in response.content
    assert b'data-search-endpoint="/v1/search"' in response.content
    assert b'data-entry-url-template="/dictionary/entries/__PUBLIC_ID__/"' in (
        response.content
    )


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
    assert b'data-tsumo-endpoint="/v1/figurative-expressions/tsumo"' in (
        response.content
    )
    assert b'data-madimikira-endpoint="/v1/figurative-expressions/madimikira"' in (
        response.content
    )
    assert b"dictionary-entry.js" in response.content
