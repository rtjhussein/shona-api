from django.test import Client
from django.urls import reverse


def test_dictionary_search_page_loads_without_api_auth():
    response = Client().get(reverse("dictionary-search"))

    assert response.status_code == 200
    assert b"Shona Dictionary" in response.content
    assert b'data-search-endpoint="/v1/search"' in response.content


def test_dictionary_search_alias_route_loads_same_public_ui():
    response = Client().get("/dictionary/")

    assert response.status_code == 200
    assert b"Shona Dictionary" in response.content
    assert b"dictionary-search.js" in response.content
