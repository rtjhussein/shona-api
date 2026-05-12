from rest_framework import serializers

from .models import Form, Lemma, Sense, ToneRecord


class LemmaCoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lemma
        fields = (
            "public_id",
            "headword",
            "normalized_headword",
            "headword_kind",
            "part_of_speech_code",
            "part_of_speech_label",
            "dialects",
            "comparative_bantu_marker",
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


class ToneRecordSerializer(serializers.ModelSerializer):
    form_public_id = serializers.SerializerMethodField()

    class Meta:
        model = ToneRecord
        fields = (
            "public_id",
            "pattern",
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
