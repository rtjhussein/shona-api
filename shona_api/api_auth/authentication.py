from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed

from .models import APIKey


class APIKeyAuthentication(authentication.BaseAuthentication):
    keyword = "Api-Key"

    def authenticate(self, request):
        raw_key = self._get_raw_key(request)
        if raw_key is None:
            return None

        api_key = APIKey.objects.get_from_raw_key(raw_key)
        if api_key is None:
            raise AuthenticationFailed("Invalid API key.")

        api_key.mark_used()
        return (api_key, api_key)

    def authenticate_header(self, request):
        return self.keyword

    def _get_raw_key(self, request):
        authorization = authentication.get_authorization_header(request).decode()
        if authorization:
            parts = authorization.split()
            if len(parts) == 2 and parts[0] == self.keyword:
                return parts[1]
            raise AuthenticationFailed("Invalid API key.")

        return request.headers.get("X-API-Key")
