from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.views import build_error_envelope, build_success_envelope
from shona_api.releases.services import get_current_release_metadata

from .models import FigurativeExpression
from .serializers import FigurativeExpressionSerializer


class FigurativeExpressionSubtypeMixin:
    subtype = None
    subtype_label = "figurative expression"
    not_found_code = "FIGURATIVE_EXPRESSION_NOT_FOUND"

    public_review_states = (
        ReviewState.APPROVED,
        ReviewState.PUBLISHED,
    )

    def get_queryset(self):
        return (
            FigurativeExpression.objects.filter(
                subtype=self.subtype,
                subtype_readiness=FigurativeExpression.SubtypeReadiness.ACTIVE,
                review_state__in=self.public_review_states,
            )
            .prefetch_related(
                "linked_lemmas",
                "linked_lemmas__noun_class",
                "linked_lemmas__noun_class__default_plural_class",
            )
            .order_by("normalized_expression", "public_id")
        )

    def get_release_metadata(self):
        return get_current_release_metadata()


class FigurativeExpressionSubtypeListView(FigurativeExpressionSubtypeMixin, APIView):
    def get(self, request):
        expressions = list(self.get_queryset())
        serializer = FigurativeExpressionSerializer(expressions, many=True)
        return Response(
            build_success_envelope(
                data={
                    "subtype": self.subtype,
                    "count": len(expressions),
                    "results": serializer.data,
                },
                release_metadata=self.get_release_metadata(),
            ),
            status=status.HTTP_200_OK,
        )


class FigurativeExpressionSubtypeDetailView(FigurativeExpressionSubtypeMixin, APIView):
    def get(self, request, public_id):
        expression = self._get_expression(public_id)
        serializer = FigurativeExpressionSerializer(expression)
        return Response(
            build_success_envelope(
                data=serializer.data,
                release_metadata=self.get_release_metadata(),
            ),
            status=status.HTTP_200_OK,
        )

    def _get_expression(self, public_id):
        try:
            return self.get_queryset().get(public_id=public_id)
        except FigurativeExpression.DoesNotExist as exc:
            raise Http404 from exc

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            public_id = self.kwargs["public_id"]
            return Response(
                build_error_envelope(
                    code=self.not_found_code,
                    message=(
                        f"No {self.subtype_label} found for public_id "
                        f"'{public_id}'"
                    ),
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().handle_exception(exc)


class TsumoListView(FigurativeExpressionSubtypeListView):
    subtype = FigurativeExpression.Subtype.TSUMO
    subtype_label = "tsumo"


class TsumoDetailView(FigurativeExpressionSubtypeDetailView):
    subtype = FigurativeExpression.Subtype.TSUMO
    subtype_label = "tsumo"
    not_found_code = "TSUMO_NOT_FOUND"
