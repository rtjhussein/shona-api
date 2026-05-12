LOCAL_ONLY_RIGHTS_NOTE = (
    "Local-only source material; do not upload source files to git. "
    "Use only as an internal implementation reference with recorded provenance."
)

SOURCE_REGISTRY = [
    {
        "source_key": "source_prd",
        "title": "Product Requirements Document",
        "authority_level": "Planning authority",
        "rights_usage_note": LOCAL_ONLY_RIGHTS_NOTE,
        "ingestion_style": "Manual reference only",
        "current_filename": "prd_v5.md",
    },
    {
        "source_key": "source_hannan",
        "title": "Hannan Dictionary",
        "authority_level": "Backbone lexical authority",
        "rights_usage_note": LOCAL_ONLY_RIGHTS_NOTE,
        "ingestion_style": (
            "Digitized dictionary-entry parsing into structured candidates, "
            "followed by editorial review"
        ),
        "current_filename": "hannan_dictionary.pdf",
    },
    {
        "source_key": "source_fortune",
        "title": "Fortune Grammatical Constructions",
        "authority_level": "Backbone grammar authority",
        "rights_usage_note": LOCAL_ONLY_RIGHTS_NOTE,
        "ingestion_style": (
            "Rule extraction and structured grammar notes, then tests/fixtures "
            "before implementation"
        ),
        "current_filename": "fortune_grammatical_constructions.pdf",
    },
    {
        "source_key": "source_fsi",
        "title": "FSI Shona Course",
        "authority_level": "Backbone learner/example authority",
        "rights_usage_note": LOCAL_ONLY_RIGHTS_NOTE,
        "ingestion_style": "Example and form extraction as reviewed learner-facing candidates",
        "current_filename": "fsi_course.pdf",
    },
    {
        "source_key": "source_maumbirwo",
        "title": "Maumbirwo eMazita",
        "authority_level": "Validation authority",
        "rights_usage_note": LOCAL_ONLY_RIGHTS_NOTE,
        "ingestion_style": "Targeted structured notes and QA fixtures",
        "current_filename": "maumbirwo_emazita.pdf",
    },
    {
        "source_key": "source_curriculum_notes",
        "title": "Curriculum Notes Forms 1-4",
        "authority_level": "Validation authority",
        "rights_usage_note": LOCAL_ONLY_RIGHTS_NOTE,
        "ingestion_style": (
            "Manual policy extraction into normalization and learner-guidance "
            "notes"
        ),
        "current_filename": "curriculum_notes_forms_1_4.pdf",
    },
    {
        "source_key": "source_zimsec_syllabus",
        "title": "ZIMSEC Syllabus Forms 1-4",
        "authority_level": "Curriculum authority",
        "rights_usage_note": LOCAL_ONLY_RIGHTS_NOTE,
        "ingestion_style": "Manual topic/tag extraction into curriculum metadata",
        "current_filename": "zimsec_syllabus_forms_1_4.pdf",
    },
    {
        "source_key": "source_tsumo_tsika",
        "title": "Tsumo Tsika",
        "authority_level": "Structured enrichment authority",
        "rights_usage_note": LOCAL_ONLY_RIGHTS_NOTE,
        "ingestion_style": "Theme and interpretation extraction as reviewed enrichment",
        "current_filename": "tsumo_tsika.pdf",
    },
    {
        "source_key": "source_shona_yedu",
        "title": "Shona Yedu",
        "authority_level": "Candidate enrichment authority",
        "rights_usage_note": LOCAL_ONLY_RIGHTS_NOTE,
        "ingestion_style": (
            "Candidate extraction only; promote after dedupe, conflict checks, "
            "and review"
        ),
        "current_filename": "shona_yedu.pdf",
    },
]
