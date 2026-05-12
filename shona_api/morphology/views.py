from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from shona_api.lexicon.views import build_error_envelope, build_success_envelope
from shona_api.releases.services import get_current_release_metadata

from .services import AnalysisFailure, analyze_text


class AnalyzeView(APIView):
    def post(self, request):
        raw_text = request.data.get("text") if isinstance(request.data, dict) else None
        if not isinstance(raw_text, str):
            return Response(
                build_error_envelope(
                    code="ANALYSIS_TEXT_REQUIRED",
                    message="Analysis requires a non-empty 'text' string.",
                    detail={"field": "text", "expected_type": "string"},
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        release_metadata = get_current_release_metadata()
        try:
            payload = analyze_text(
                raw_text,
                rule_set_version=release_metadata["rule_set_version"],
            )
        except AnalysisFailure as exc:
            return Response(
                build_error_envelope(
                    code=exc.code,
                    message=exc.message,
                    detail=exc.detail,
                ),
                status=_status_for_failure(exc),
            )

        return Response(
            build_success_envelope(
                data=payload,
                release_metadata=release_metadata,
            ),
            status=status.HTTP_200_OK,
        )


def _status_for_failure(exc):
    if exc.code == "ANALYSIS_TEXT_REQUIRED":
        return status.HTTP_400_BAD_REQUEST
    return status.HTTP_422_UNPROCESSABLE_ENTITY
