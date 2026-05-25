import os
import re
from typing import List, Optional
from pydantic import BaseModel, Field
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma, Sense

# Define structured Pydantic schema for Gemini structured output
class LemmaPedagogyClassifications(BaseModel):
    public_id: str = Field(description="The unique public_id of the Lemma.")
    curriculum_stage: str = Field(
        description="Must be exactly one of: 'forms_1_2', 'forms_3_4', or 'general_secondary'."
    )
    curriculum_domains: List[str] = Field(
        description="List of domain labels from: 'orthography', 'grammar', 'vocabulary', 'composition', 'comprehension', 'register', 'oral_communication', 'figurative_language', 'culture'."
    )
    learning_functions: List[str] = Field(
        description="List of function labels from: 'vocabulary', 'example_sentence', 'dialogue_practice', 'writing_guidance', 'usage_warning', 'cultural_interpretation', 'assessment_support'."
    )
    communication_contexts: List[str] = Field(
        description="List of context labels from: 'conversation', 'narrative', 'description', 'letter_writing', 'school_composition', 'formal_speech', 'greetings', 'family', 'environment', 'time'."
    )
    register_tags: List[str] = Field(
        description="List of register tags from: 'formal', 'informal', 'respectful', 'school_appropriate', 'avoid_in_school_context'."
    )

class BatchPedagogyClassification(BaseModel):
    classifications: List[LemmaPedagogyClassifications]


class Command(BaseCommand):
    help = "Tag Lemmas with ZIMSEC Syllabus Levels and Communication Contexts using rule-based and LLM-assisted classifiers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without saving changes to the database.",
        )
        parser.add_argument(
            "--llm",
            action="store_true",
            help="Enable LLM-assisted batch classification using Gemini 2.5 Flash.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=30,
            help="Batch size for LLM classification.",
        )
        parser.add_argument(
            "--max-lemmas",
            type=int,
            default=150,
            help="Maximum number of lemmas to process with LLM.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        use_llm = options["llm"]
        batch_size = options["batch_size"]
        max_lemmas = options["max_lemmas"]

        self.stdout.write(self.style.NOTICE("Starting rule-based curriculum tagging..."))
        rule_updated_count = self._run_rule_based_tagging(dry_run)
        self.stdout.write(self.style.SUCCESS(f"Rule-based tagging completed. Updated {rule_updated_count} lemmas."))

        if use_llm:
            api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
            if not api_key:
                self.stderr.write(self.style.ERROR("Error: GEMINI_API_KEY not found in environment or settings. Skipping LLM steps."))
                return

            self.stdout.write(self.style.NOTICE(f"Starting LLM-assisted tagging (max {max_lemmas} lemmas, batch size {batch_size})..."))
            llm_updated_count = self._run_llm_based_tagging(api_key, dry_run, batch_size, max_lemmas)
            self.stdout.write(self.style.SUCCESS(f"LLM-assisted tagging completed. Updated {llm_updated_count} lemmas."))

    def _run_rule_based_tagging(self, dry_run: bool) -> int:
        from shona_api.lexicon.learner_metadata import apply_rule_based_curriculum_tags

        updated_count = 0
        lemmas = Lemma.objects.filter(review_state=ReviewState.PUBLISHED).prefetch_related("senses")

        for lemma in lemmas:
            if not dry_run:
                updated = apply_rule_based_curriculum_tags(lemma)
                if updated:
                    self.stdout.write(f"Rule-matched and updated: '{lemma.headword}'")
                    updated_count += 1
            else:
                # Dry run matching simulation
                import re
                keywords = {
                    "greetings": re.compile(r"\b(?:mhoro|kwaziwai|greet|welcome|say hello|hello|greeting)\b", re.I),
                    "family": re.compile(r"\b(?:amai|baba|hanzvadzi|child|son|daughter|mother|father|brother|sister|aunt|uncle|family)\b", re.I),
                    "environment": re.compile(r"\b(?:musha|gomo|rwizi|mhuka|sango|river|mountain|animal|forest|tree|rain|sun|weather|nature)\b", re.I),
                    "time": re.compile(r"\b(?:nguva|zuva|mwaka|nhasi|mangwana|time|hour|day|year|yesterday|tomorrow|month)\b", re.I)
                }
                definitions_text = " ".join([sense.definition for sense in lemma.senses.all()])
                text_to_match = f"{lemma.headword} {lemma.normalized_headword} {definitions_text}"
                matched_contexts = [key for key, rx in keywords.items() if rx.search(text_to_match)]
                if matched_contexts:
                    self.stdout.write(f"Rule-matched (dry-run): '{lemma.headword}' with contexts={matched_contexts}")
                    updated_count += 1
        return updated_count

    def _run_llm_based_tagging(self, api_key: str, dry_run: bool, batch_size: int, max_lemmas: int) -> int:
        from google import genai
        from google.genai import types

        # Find lemmas with UNKNOWN curriculum stage to tag
        lemmas_to_tag = Lemma.objects.filter(
            review_state=ReviewState.PUBLISHED,
            curriculum_stage=Lemma.CurriculumStage.UNKNOWN
        ).prefetch_related("senses")[:max_lemmas]

        if not lemmas_to_tag:
            self.stdout.write("No untagged lemmas found for LLM classification.")
            return 0

        client = genai.Client(api_key=api_key)
        updated_count = 0

        # Batch processing
        lemma_list = list(lemmas_to_tag)
        for i in range(0, len(lemma_list), batch_size):
            batch = lemma_list[i:i+batch_size]
            self.stdout.write(f"Processing batch of {len(batch)} lemmas...")

            # Format batch context
            serialized_lemmas = []
            for l in batch:
                senses_str = "; ".join([f"Sense {s.number}: {s.definition}" for s in l.senses.all()])
                serialized_lemmas.append(
                    f"- public_id: {l.public_id}\n"
                    f"  headword: {l.headword}\n"
                    f"  pos: {l.part_of_speech_code}\n"
                    f"  senses: {senses_str}"
                )
            
            lemmas_payload = "\n\n".join(serialized_lemmas)

            system_prompt = (
                "You are an expert Shona language educator and ZIMSEC Shona curriculum curriculum designer. "
                "Classify the provided list of Shona lemmas into appropriate ZIMSEC syllabus levels, curriculum domains, "
                "learning functions, communication contexts, and register tags using their headwords and sense definitions. "
                "Strictly follow the defined guidelines and taxonomy.\n\n"
                "TAXONOMY DETAILS:\n"
                "- curriculum_stage: 'forms_1_2' (Forms 1-2: standard everyday words, greetings, family, simple descriptors), "
                "  'forms_3_4' (Forms 3-4: advanced vocabulary, deep cultural/literary context, proverbs, idioms, business, complex domains), "
                "  'general_secondary' (general secondary terms)\n"
                "- curriculum_domains: 'orthography', 'grammar', 'vocabulary', 'composition', 'comprehension', 'register', 'oral_communication', 'figurative_language', 'culture'\n"
                "- learning_functions: 'vocabulary', 'example_sentence', 'dialogue_practice', 'writing_guidance', 'usage_warning', 'cultural_interpretation', 'assessment_support'\n"
                "- communication_contexts: 'conversation', 'narrative', 'description', 'letter_writing', 'school_composition', 'formal_speech', 'greetings', 'family', 'environment', 'time'\n"
                "- register_tags: 'formal', 'informal', 'respectful', 'school_appropriate', 'avoid_in_school_context'\n\n"
                "Return classifications matching the requested JSON schema."
            )

            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        system_prompt,
                        f"Please classify the following Shona lemmas:\n\n{lemmas_payload}"
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=BatchPedagogyClassification,
                        temperature=0.1,
                    )
                )

                import json
                result = json.loads(response.text)
                classifications = result.get("classifications", [])

                for classification in classifications:
                    pid = classification["public_id"]
                    lemma_obj = Lemma.objects.filter(public_id=pid).first()
                    if not lemma_obj:
                        continue
                    
                    self.stdout.write(
                        f"LLM-tagged '{lemma_obj.headword}': "
                        f"stage={classification['curriculum_stage']}, "
                        f"domains={classification['curriculum_domains']}, "
                        f"contexts={classification['communication_contexts']}"
                    )

                    if not dry_run:
                        with transaction.atomic():
                            lemma_obj = Lemma.objects.select_for_update().get(pk=lemma_obj.pk)
                            lemma_obj.curriculum_stage = classification["curriculum_stage"]
                            lemma_obj.curriculum_domains = list(set(lemma_obj.curriculum_domains + classification["curriculum_domains"]))
                            lemma_obj.learning_functions = list(set(lemma_obj.learning_functions + classification["learning_functions"]))
                            lemma_obj.communication_contexts = list(set(lemma_obj.communication_contexts + classification["communication_contexts"]))
                            lemma_obj.register_tags = list(set(lemma_obj.register_tags + classification["register_tags"]))
                            
                            source_link = {
                                "source_key": "source_zimsec_syllabus",
                                "source_locator": "zimsec_syllabus_forms_1_4.pdf:llm_classify",
                                "review_status": "reviewed",
                                "mapping_method": "llm_pedagogy_tagging_v1",
                                "note": "Classified using Gemini 2.5 Flash curriculum mapping model."
                            }
                            lemma_obj.learner_source_links = [*lemma_obj.learner_source_links, source_link]
                            lemma_obj.save()
                        updated_count += 1

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error during LLM classification batch: {e}"))
                continue

        return updated_count
