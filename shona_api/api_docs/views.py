from django.http import JsonResponse
from django.views import View

from .spec import build_openapi_spec


class OpenAPISpecView(View):
    def get(self, request):
        return JsonResponse(
            build_openapi_spec(),
            json_dumps_params={"indent": 2},
        )
