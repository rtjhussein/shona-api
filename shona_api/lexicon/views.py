from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from shona_api.releases.services import get_current_release_metadata

from .models import Lemma
from .serializers import LemmaReadSerializer


def build_success_envelope(*, data, release_metadata):
    return {
        "api_version": "v1",
        "data_release": release_metadata["release_version"],
        "rule_set_version": release_metadata["rule_set_version"],
        "generated_at": timezone.now().isoformat().replace("+00:00", "Z"),
        "data": data,
    }


def build_error_envelope(*, code, message, detail=None):
    return {
        "api_version": "v1",
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
        },
    }


class LemmaReadView(APIView):
    def get(self, request, public_id):
        lemma = self._get_lemma(public_id)
        serializer = LemmaReadSerializer(lemma)
        release_metadata = get_current_release_metadata()
        return Response(
            build_success_envelope(
                data=serializer.data,
                release_metadata=release_metadata,
            ),
            status=status.HTTP_200_OK,
        )

    def _get_lemma(self, public_id):
        try:
            return (
                Lemma.objects.prefetch_related(
                    "senses",
                    "tone_records__form",
                    "forms__sense",
                )
                .get(public_id=public_id)
            )
        except Lemma.DoesNotExist as exc:
            raise Http404 from exc

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            public_id = self.kwargs["public_id"]
            return Response(
                build_error_envelope(
                    code="LEMMA_NOT_FOUND",
                    message=f"No lemma found for public_id '{public_id}'",
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().handle_exception(exc)
