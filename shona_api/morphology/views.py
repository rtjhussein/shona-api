from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from shona_api.lexicon.views import (
    build_current_release_missing_response,
    build_error_envelope,
    build_success_envelope,
)
from shona_api.releases.services import CurrentReleaseNotFound, get_current_release_metadata

from .services import AnalysisFailure, GenerationFailure, analyze_text, generate_form


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

        try:
            release_metadata = get_current_release_metadata()
        except CurrentReleaseNotFound:
            return build_current_release_missing_response()

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


class GenerateView(APIView):
    def post(self, request):
        lemma_public_id = (
            request.data.get("lemma_public_id")
            if isinstance(request.data, dict)
            else None
        )
        if not isinstance(lemma_public_id, str) or not lemma_public_id.strip():
            return Response(
                build_error_envelope(
                    code="GENERATION_LEMMA_REQUIRED",
                    message="Generation requires a non-empty 'lemma_public_id' string.",
                    detail={"field": "lemma_public_id", "expected_type": "string"},
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        features = (
            request.data.get("features") if isinstance(request.data, dict) else None
        )
        if not isinstance(features, dict):
            return Response(
                build_error_envelope(
                    code="GENERATION_FEATURES_REQUIRED",
                    message="Generation requires a structured 'features' object.",
                    detail={"field": "features", "expected_type": "object"},
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            release_metadata = get_current_release_metadata()
        except CurrentReleaseNotFound:
            return build_current_release_missing_response()

        try:
            payload = generate_form(
                lemma_public_id=lemma_public_id.strip(),
                features=features,
                rule_set_version=release_metadata["rule_set_version"],
            )
        except GenerationFailure as exc:
            return Response(
                build_error_envelope(
                    code=exc.code,
                    message=exc.message,
                    detail=exc.detail,
                ),
                status=_status_for_generation_failure(exc),
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


def _status_for_generation_failure(exc):
    if exc.code in {"GENERATION_LEMMA_REQUIRED", "GENERATION_FEATURES_REQUIRED"}:
        return status.HTTP_400_BAD_REQUEST
    return status.HTTP_422_UNPROCESSABLE_ENTITY
