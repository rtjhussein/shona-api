from django.urls import reverse


API_VERSION = "v1"
SPEC_VERSION = "2026.05.0"


def build_openapi_spec():
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Shona API",
            "version": SPEC_VERSION,
            "summary": "Public API for reviewed Shona lexical and language data.",
            "description": (
                "The Shona API exposes reviewed lexical records, exact search, "
                "active figurative-language records, and bounded morphology v1 "
                "analysis/generation. Protected endpoints accept API keys through "
                "the Authorization header using the Api-Key scheme or through "
                "the X-API-Key header."
            ),
        },
        "servers": [
            {
                "url": "http://localhost:8000",
                "description": "Local development server",
            }
        ],
        "tags": [
            {"name": "System"},
            {"name": "Lexicon"},
            {"name": "Figurative language"},
            {"name": "Morphology"},
        ],
        "paths": {
            reverse("health"): {
                "get": {
                    "tags": ["System"],
                    "summary": "Check service health.",
                    "operationId": "getHealth",
                    "security": [],
                    "responses": {
                        "200": {
                            "description": "Service health state.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Health"}
                                }
                            },
                        }
                    },
                }
            },
            reverse("search"): {
                "get": {
                    "tags": ["Lexicon"],
                    "summary": "Search reviewed lemmas and forms.",
                    "description": (
                        "Search exact reviewed lemmas/forms and attach morphology "
                        "enrichment for supported forms such as ndinobuda or kubuda. "
                        "Unsupported shapes can include future-lane rule-card hints."
                    ),
                    "operationId": "searchLexicon",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "description": (
                                "Search query, for example a lemma, form, or "
                                "supported morphology surface."
                            ),
                            "schema": {"type": "string", "minLength": 1},
                            "examples": {
                                "lemma": {"value": "buda"},
                                "infinitive": {"value": "kubuda"},
                            },
                        }
                    ],
                    "responses": {
                        "200": success_response(
                            "Search results.",
                            {"$ref": "#/components/schemas/SearchData"},
                        ),
                        "400": error_response("Missing or empty search query."),
                        "401": auth_error_response(),
                        "429": rate_limit_response(),
                        "503": current_release_response(),
                    },
                    "security": [{"ApiKeyAuth": []}],
                }
            },
            path_with_public_id("lemma-read"): {
                "get": {
                    "tags": ["Lexicon"],
                    "summary": "Read one lexical entry by public ID.",
                    "operationId": "getLemma",
                    "parameters": [public_id_parameter("Lemma public ID.", "lemma_abc123")],
                    "responses": {
                        "200": success_response(
                            "Lemma detail.",
                            {"$ref": "#/components/schemas/LemmaReadData"},
                        ),
                        "401": auth_error_response(),
                        "404": error_response("No lemma exists for that public ID."),
                        "429": rate_limit_response(),
                        "503": current_release_response(),
                    },
                    "security": [{"ApiKeyAuth": []}],
                }
            },
            reverse("tsumo-list"): {
                "get": {
                    "tags": ["Figurative language"],
                    "summary": "List active reviewed tsumo records.",
                    "operationId": "listTsumo",
                    "responses": {
                        "200": success_response(
                            "Tsumo list.",
                            {"$ref": "#/components/schemas/FigurativeExpressionListData"},
                        ),
                        "401": auth_error_response(),
                        "429": rate_limit_response(),
                        "503": current_release_response(),
                    },
                    "security": [{"ApiKeyAuth": []}],
                }
            },
            path_with_public_id("tsumo-detail"): {
                "get": {
                    "tags": ["Figurative language"],
                    "summary": "Read one active reviewed tsumo record.",
                    "operationId": "getTsumo",
                    "parameters": [public_id_parameter("Tsumo public ID.", "figexpr_abc123")],
                    "responses": {
                        "200": success_response(
                            "Tsumo detail.",
                            {"$ref": "#/components/schemas/FigurativeExpression"},
                        ),
                        "401": auth_error_response(),
                        "404": error_response("No tsumo exists for that public ID."),
                        "429": rate_limit_response(),
                        "503": current_release_response(),
                    },
                    "security": [{"ApiKeyAuth": []}],
                }
            },
            reverse("madimikira-list"): {
                "get": {
                    "tags": ["Figurative language"],
                    "summary": "List active reviewed madimikira records.",
                    "operationId": "listMadimikira",
                    "responses": {
                        "200": success_response(
                            "Madimikira list.",
                            {"$ref": "#/components/schemas/FigurativeExpressionListData"},
                        ),
                        "401": auth_error_response(),
                        "429": rate_limit_response(),
                        "503": current_release_response(),
                    },
                    "security": [{"ApiKeyAuth": []}],
                }
            },
            path_with_public_id("madimikira-detail"): {
                "get": {
                    "tags": ["Figurative language"],
                    "summary": "Read one active reviewed madimikira record.",
                    "operationId": "getMadimikira",
                    "parameters": [
                        public_id_parameter("Madimikira public ID.", "figexpr_abc123")
                    ],
                    "responses": {
                        "200": success_response(
                            "Madimikira detail.",
                            {"$ref": "#/components/schemas/FigurativeExpression"},
                        ),
                        "401": auth_error_response(),
                        "404": error_response("No madimikira exists for that public ID."),
                        "429": rate_limit_response(),
                        "503": current_release_response(),
                    },
                    "security": [{"ApiKeyAuth": []}],
                }
            },
            reverse("analyze"): {
                "post": {
                    "tags": ["Morphology"],
                    "summary": "Analyze a supported v1 Shona form.",
                    "description": (
                        "Supports simple ku- infinitives built from reviewed verb "
                        "stems plus bounded present positive/negative verb forms."
                    ),
                    "operationId": "analyzeForm",
                    "requestBody": json_body(
                        {"$ref": "#/components/schemas/AnalyzeRequest"},
                        {"text": "kubuda"},
                    ),
                    "responses": {
                        "200": success_response(
                            "Morphological analysis.",
                            {"$ref": "#/components/schemas/AnalyzeData"},
                        ),
                        "400": error_response("Text is missing or not a string."),
                        "401": auth_error_response(),
                        "422": error_response("The form is outside v1 support."),
                        "429": rate_limit_response(),
                        "503": current_release_response(),
                    },
                    "security": [{"ApiKeyAuth": []}],
                }
            },
            reverse("generate"): {
                "post": {
                    "tags": ["Morphology"],
                    "summary": "Generate a supported v1 Shona verb form.",
                    "operationId": "generateForm",
                    "requestBody": json_body(
                        {"$ref": "#/components/schemas/GenerateRequest"},
                        {
                            "lemma_public_id": "lemma_abc123",
                            "features": {
                                "generation_type": "verb_form",
                                "subject": {
                                    "type": "person",
                                    "person": "first",
                                    "number": "singular",
                                },
                                "tense_aspect": "present",
                                "polarity": "positive",
                            },
                        },
                    ),
                    "responses": {
                        "200": success_response(
                            "Generated form.",
                            {"$ref": "#/components/schemas/GenerateData"},
                        ),
                        "400": error_response("Required generation input is missing."),
                        "401": auth_error_response(),
                        "422": error_response("Requested features are outside v1 support."),
                        "429": rate_limit_response(),
                        "503": current_release_response(),
                    },
                    "security": [{"ApiKeyAuth": []}],
                }
            },
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "Authorization",
                    "description": "Use the form: Api-Key shona_sk_...",
                },
                "XApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "Alternative API key header.",
                },
            },
            "schemas": schemas(),
        },
    }


def path_with_public_id(route_name):
    return reverse(route_name, kwargs={"public_id": "public_id"}).replace(
        "public_id",
        "{public_id}",
    )


def public_id_parameter(description, example):
    return {
        "name": "public_id",
        "in": "path",
        "required": True,
        "description": description,
        "schema": {"type": "string"},
        "example": example,
    }


def success_response(description, data_schema):
    return {
        "description": description,
        "headers": rate_limit_headers(),
        "content": {
            "application/json": {
                "schema": {
                    "allOf": [
                        {"$ref": "#/components/schemas/SuccessEnvelope"},
                        {
                            "type": "object",
                            "properties": {"data": data_schema},
                            "required": ["data"],
                        },
                    ]
                }
            }
        },
    }


def error_response(description):
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"}
            }
        },
    }


def auth_error_response():
    return error_response("API key is missing or invalid.")


def rate_limit_response():
    response = error_response("API key rate limit exceeded.")
    response["headers"] = rate_limit_headers()
    return response


def current_release_response():
    return error_response("Current data release is not configured.")


def rate_limit_headers():
    return {
        "X-RateLimit-Limit": {
            "schema": {"type": "integer"},
            "description": "Allowed requests per minute for the API key.",
        },
        "X-RateLimit-Remaining": {
            "schema": {"type": "integer"},
            "description": "Remaining requests in the current window.",
        },
        "X-RateLimit-Reset": {
            "schema": {"type": "integer"},
            "description": "Seconds until the current rate-limit window resets.",
        },
        "X-RateLimit-Plan": {
            "schema": {"type": "string"},
            "description": "Plan attached to the API key.",
        },
    }


def json_body(schema, example):
    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": schema,
                "example": example,
            }
        },
    }


def schemas():
    json_object = {"type": "object", "additionalProperties": True}
    string_array = {"type": "array", "items": {"type": "string"}}
    return {
        "Health": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "ok"},
                "version": {"type": "string", "example": "0.1.0"},
            },
            "required": ["status", "version"],
        },
        "SuccessEnvelope": {
            "type": "object",
            "properties": {
                "api_version": {"type": "string", "example": API_VERSION},
                "data_release": {"type": "string", "example": "2026.05.0"},
                "rule_set_version": {
                    "type": "string",
                    "example": "morphology-rules-v2",
                },
                "generated_at": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2026-05-12T12:00:00Z",
                },
                "data": json_object,
            },
            "required": [
                "api_version",
                "data_release",
                "rule_set_version",
                "generated_at",
                "data",
            ],
        },
        "ErrorEnvelope": {
            "type": "object",
            "properties": {
                "api_version": {"type": "string", "example": API_VERSION},
                "error": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "example": "LEMMA_NOT_FOUND"},
                        "message": {"type": "string"},
                        "detail": {"oneOf": [json_object, {"type": "null"}]},
                    },
                    "required": ["code", "message", "detail"],
                },
            },
            "required": ["api_version", "error"],
        },
        "SearchData": {
            "type": "object",
            "properties": {
                "query": {"$ref": "#/components/schemas/NormalizedQuery"},
                "count": {"type": "integer"},
                "results": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/SearchResult"},
                },
                "morphology": {"$ref": "#/components/schemas/AnalyzeData"},
                "morphology_enrichment": {
                    "$ref": "#/components/schemas/MorphologyEnrichmentStatus"
                },
                "zero_result": json_object,
            },
            "required": ["query", "count", "results"],
        },
        "MorphologyEnrichmentStatus": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["matched", "unsupported", "failed"],
                },
                "count": {"type": "integer"},
                "code": {"type": "string"},
                "message": {"type": "string"},
                "detail": json_object,
            },
            "required": ["status"],
            "additionalProperties": True,
        },
        "SearchResult": {
            "type": "object",
            "properties": {
                "result_type": {"type": "string", "enum": ["lemma", "form"]},
                "match_type": {"type": "string", "example": "exact_lemma"},
                "lemma": {"$ref": "#/components/schemas/LemmaCore"},
                "form": {"$ref": "#/components/schemas/Form"},
            },
            "required": ["result_type", "match_type", "lemma"],
        },
        "LemmaReadData": {
            "type": "object",
            "properties": {
                "lemma": {"$ref": "#/components/schemas/LemmaCore"},
                "senses": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/Sense"},
                },
                "tone_records": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/ToneRecord"},
                },
                "forms": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/Form"},
                },
            },
            "required": ["lemma", "senses", "tone_records", "forms"],
        },
        "LemmaCore": {
            "type": "object",
            "properties": {
                "public_id": {"type": "string"},
                "headword": {"type": "string"},
                "normalized_headword": {"type": "string"},
                "headword_kind": {"type": "string"},
                "part_of_speech_code": {"type": "string"},
                "part_of_speech_label": {"type": "string"},
                "noun_class": {
                    "oneOf": [
                        {"$ref": "#/components/schemas/NounClass"},
                        {"type": "null"},
                    ]
                },
                "dialects": string_array,
                "learner_level": {"type": "string"},
                "curriculum_stage": {"type": "string"},
                "review_state": {"type": "string"},
            },
            "required": [
                "public_id",
                "headword",
                "normalized_headword",
                "headword_kind",
                "part_of_speech_code",
                "part_of_speech_label",
                "noun_class",
            ],
            "additionalProperties": True,
        },
        "NounClass": {
            "type": "object",
            "properties": {
                "public_id": {"type": "string"},
                "class_number": {"type": "string"},
                "label": {"type": "string"},
                "nominal_prefix": {"type": "string"},
                "default_plural_class_number": {
                    "oneOf": [{"type": "string"}, {"type": "null"}]
                },
            },
            "required": ["public_id", "class_number", "label"],
            "additionalProperties": True,
        },
        "Sense": {
            "type": "object",
            "properties": {
                "public_id": {"type": "string"},
                "number": {"type": "integer"},
                "definition": {"type": "string"},
                "dialects": string_array,
                "grammar": string_array,
                "examples": {"type": "array", "items": True},
                "cross_references": {"type": "array", "items": True},
            },
            "required": ["public_id", "number", "definition"],
            "additionalProperties": True,
        },
        "ToneRecord": {
            "type": "object",
            "properties": {
                "public_id": {"type": "string"},
                "pattern": {"type": "string"},
                "dialects": {"type": "array", "items": {"type": "string"}},
                "notation_system": {"type": "string"},
                "note": {"type": "string"},
                "form_public_id": {
                    "oneOf": [{"type": "string"}, {"type": "null"}]
                },
            },
            "required": ["public_id", "pattern", "notation_system"],
            "additionalProperties": True,
        },
        "Form": {
            "type": "object",
            "properties": {
                "public_id": {"type": "string"},
                "form_text": {"type": "string"},
                "normalized_form": {"type": "string"},
                "form_kind": {"type": "string"},
                "dialects": string_array,
                "grammar": string_array,
                "derived_form_evidence": json_object,
                "sense_public_id": {
                    "oneOf": [{"type": "string"}, {"type": "null"}]
                },
            },
            "required": ["public_id", "form_text", "normalized_form", "form_kind"],
            "additionalProperties": True,
        },
        "FigurativeExpressionListData": {
            "type": "object",
            "properties": {
                "subtype": {"type": "string", "enum": ["tsumo", "madimikira"]},
                "count": {"type": "integer"},
                "results": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/FigurativeExpression"},
                },
            },
            "required": ["subtype", "count", "results"],
        },
        "FigurativeExpression": {
            "type": "object",
            "properties": {
                "public_id": {"type": "string"},
                "subtype": {"type": "string"},
                "subtype_readiness": {"type": "string"},
                "text": {"type": "string"},
                "normalized_text": {"type": "string"},
                "meaning": {"type": "string"},
                "english_rendering": {"type": "string"},
                "usage_note": {"type": "string"},
                "cultural_themes": string_array,
                "linked_lemmas": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/LemmaCore"},
                },
                "review_status": {"type": "string"},
            },
            "required": [
                "public_id",
                "subtype",
                "subtype_readiness",
                "text",
                "normalized_text",
                "meaning",
                "linked_lemmas",
                "review_status",
            ],
            "additionalProperties": True,
        },
        "NormalizedQuery": {
            "type": "object",
            "properties": {
                "raw": {"type": "string"},
                "normalized": {"type": "string"},
                "normalizer": {"type": "string"},
            },
            "required": ["raw", "normalized", "normalizer"],
        },
        "AnalyzeRequest": {
            "type": "object",
            "properties": {"text": {"type": "string", "example": "kubuda"}},
            "required": ["text"],
        },
        "AnalyzeData": {
            "type": "object",
            "properties": {
                "query": {"$ref": "#/components/schemas/NormalizedQuery"},
                "analyzer_version": {"type": "string"},
                "rule_set_version": {"type": "string"},
                "count": {"type": "integer"},
                "analyses": {"type": "array", "items": json_object},
            },
            "required": [
                "query",
                "analyzer_version",
                "rule_set_version",
                "count",
                "analyses",
            ],
        },
        "GenerateRequest": {
            "type": "object",
            "properties": {
                "lemma_public_id": {"type": "string"},
                "features": json_object,
            },
            "required": ["lemma_public_id", "features"],
        },
        "GenerateData": {
            "type": "object",
            "properties": {
                "input": json_object,
                "generator_version": {"type": "string"},
                "rule_set_version": {"type": "string"},
                "confidence": {"type": "number"},
                "generated": json_object,
                "warnings": {"type": "array", "items": json_object},
                "metadata": json_object,
            },
            "required": [
                "input",
                "generator_version",
                "rule_set_version",
                "confidence",
                "generated",
                "warnings",
                "metadata",
            ],
        },
    }
