from rest_framework import serializers

from .examples import normalize_example_pairs
from .models import Form, Lemma, NounClass, Sense, ToneRecord


class NounClassSerializer(serializers.ModelSerializer):
    default_plural_class_number = serializers.SerializerMethodField()

    class Meta:
        model = NounClass
        fields = (
            "public_id",
            "class_number",
            "label",
            "nominal_prefix",
            "prefix_allomorphs",
            "default_plural_class_number",
            "subject_concord",
            "object_concord",
            "possessive_concord",
            "adjectival_concord",
            "relative_concord",
            "associative_concord",
            "demonstrative_proximal",
            "demonstrative_medial",
            "demonstrative_distal",
            "additional_concords",
            "dialect_overrides",
            "provenance",
            "revision",
            "review_state",
        )

    def get_default_plural_class_number(self, obj):
        return (
            obj.default_plural_class.class_number
            if obj.default_plural_class is not None
            else None
        )


class LemmaCoreSerializer(serializers.ModelSerializer):
    noun_class = NounClassSerializer(read_only=True)

    class Meta:
        model = Lemma
        fields = (
            "public_id",
            "headword",
            "normalized_headword",
            "headword_kind",
            "part_of_speech_code",
            "part_of_speech_label",
            "noun_class",
            "dialects",
            "comparative_bantu_marker",
            "learner_level",
            "curriculum_stage",
            "curriculum_domains",
            "learning_functions",
            "communication_contexts",
            "register_tags",
            "learner_source_links",
            "first_appearance_source_key",
            "first_appearance_locator",
            "first_appearance_unit",
            "first_appearance_lesson",
            "first_appearance_page",
            "frequency_tier",
            "frequency_score",
            "phonology_inventory_version",
            "graphemes",
            "grapheme_count",
            "syllables",
            "syllable_count",
            "provenance",
            "revision",
            "review_state",
        )


class SenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sense
        fields = (
            "public_id",
            "number",
            "definition",
            "dialects",
            "grammar",
            "examples",
            "cross_references",
            "provenance",
            "revision",
            "review_state",
        )

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data["examples"] = normalize_example_pairs(obj.examples)
        return data


class ToneRecordSerializer(serializers.ModelSerializer):
    form_public_id = serializers.SerializerMethodField()

    class Meta:
        model = ToneRecord
        fields = (
            "public_id",
            "pattern",
            "dialects",
            "notation_system",
            "note",
            "form_public_id",
            "provenance",
            "revision",
            "review_state",
        )

    def get_form_public_id(self, obj):
        return obj.form.public_id if obj.form is not None else None


class FormSerializer(serializers.ModelSerializer):
    sense_public_id = serializers.SerializerMethodField()

    class Meta:
        model = Form
        fields = (
            "public_id",
            "form_text",
            "normalized_form",
            "form_kind",
            "dialects",
            "grammar",
            "sense_public_id",
            "phonology_inventory_version",
            "graphemes",
            "grapheme_count",
            "syllables",
            "syllable_count",
            "provenance",
            "revision",
            "review_state",
        )

    def get_sense_public_id(self, obj):
        return obj.sense.public_id if obj.sense is not None else None

    def to_representation(self, obj):
        data = super().to_representation(obj)
        evidence = (
            obj.provenance.get("derived_form_evidence")
            if isinstance(obj.provenance, dict)
            else None
        )
        if obj.form_kind == Form.FormKind.DERIVED and evidence:
            data["derived_form_evidence"] = evidence
        return data


class LemmaReadSerializer(serializers.Serializer):
    def to_representation(self, lemma):
        return {
            "lemma": LemmaCoreSerializer(lemma).data,
            "senses": SenseSerializer(lemma.senses.all(), many=True).data,
            "tone_records": ToneRecordSerializer(
                lemma.tone_records.all(),
                many=True,
            ).data,
            "forms": FormSerializer(lemma.forms.all(), many=True).data,
        }


class SearchResultSerializer(serializers.Serializer):
    def to_representation(self, result):
        lemma = result["lemma"]
        lemma_data = LemmaCoreSerializer(lemma).data
        lemma_data["senses"] = SenseSerializer(lemma.senses.all(), many=True).data
        lemma_data["tone_records"] = ToneRecordSerializer(lemma.tone_records.all(), many=True).data
        lemma_data["forms"] = FormSerializer(lemma.forms.all(), many=True).data

        payload = {
            "result_type": result["result_type"],
            "match_type": result["match_type"],
            "lemma": lemma_data,
        }
        if result["form"] is not None:
            payload["form"] = FormSerializer(result["form"]).data
        return payload
