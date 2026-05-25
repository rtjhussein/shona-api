import os
import re
import string
from django.core.management.base import BaseCommand
from django.conf import settings
from shona_api.lexicon.models import Lemma, Form
from shona_api.lexicon.learner_metadata import map_fsi_learner_metadata
from shona_api.morphology.services import analyze_text, AnalysisFailure

class Command(BaseCommand):
    help = "Parse FSI Shona Course PDF, clean/tokenize text, map tokens to base lemmas, and update pedagogical metadata."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without saving changes to the database.",
        )

    def handle(self, *args, **options):
        # 1. Open PDF
        pdf_path = os.path.join(settings.BASE_DIR, "key_documents", "fsi_course.pdf")
        if not os.path.exists(pdf_path):
            self.stderr.write(self.style.ERROR(f"FSI Course PDF not found at {pdf_path}"))
            return

        import fitz  # PyMuPDF
        self.stdout.write(self.style.NOTICE(f"Opening FSI Course PDF at {pdf_path}..."))
        doc = fitz.open(pdf_path)
        self.stdout.write(self.style.SUCCESS(f"Opened PDF successfully. Total pages: {len(doc)}"))

        # Lesson tracking
        current_lesson = None
        # We will keep a dict: lemma_id -> list of appearances (lesson, page, context_line)
        lemma_appearances = {}

        # Precompiled regex for lesson numbers (e.g. UNIT 1, LESSON 1, Lesson 1)
        lesson_regex = re.compile(r"\b(?:LESSON|Lesson|UNIT|Unit)\s+(\d+)\b")
        # Precompiled regex to clean tokens (keep letters, numbers, and apostrophes/hyphens inside)
        token_regex = re.compile(r"^[a-zA-Z0-9']+(?:-[a-zA-Z0-9']+)*$")

        self.stdout.write(self.style.NOTICE("Parsing pages and extracting tokens..."))
        
        # Iterate through all pages
        for page_idx in range(len(doc)):
            page_number = page_idx + 1
            page = doc[page_idx]
            text = page.get_text("text")
            
            lines = text.splitlines()
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                # Check if this line signals a new lesson/unit
                lesson_match = lesson_regex.search(line_stripped)
                if lesson_match:
                    new_lesson = int(lesson_match.group(1))
                    if current_lesson != new_lesson:
                        current_lesson = new_lesson
                        self.stdout.write(self.style.NOTICE(f"Detected Lesson {current_lesson} on page {page_number}"))
                
                # Split line into words
                words = line_stripped.split()
                for word in words:
                    # Strip standard leading/trailing punctuation
                    cleaned_word = word.strip(string.punctuation + "“”‘’")
                    if not cleaned_word:
                        continue
                    
                    # Ensure it looks like a valid Shona/English word token
                    if not token_regex.match(cleaned_word):
                        continue
                    
                    token = cleaned_word.lower()
                    
                    # Try to map token to a Lemma
                    lemma_obj = self._resolve_token_to_lemma(token)
                    if lemma_obj:
                        if lemma_obj.pk not in lemma_appearances:
                            lemma_appearances[lemma_obj.pk] = []
                        lemma_appearances[lemma_obj.pk].append({
                            "lesson": current_lesson if current_lesson is not None else 1,
                            "page": page_number,
                            "context": line_stripped[:200]  # truncate to prevent excessive size
                        })

        self.stdout.write(self.style.SUCCESS(f"Tokenization complete. Resolved {len(lemma_appearances)} distinct lemmas."))

        # 2. Ingest pedagogy metadata
        dry_run = options["dry_run"]
        updated_count = 0

        for lemma_pk, appearances in lemma_appearances.items():
            lemma = Lemma.objects.get(pk=lemma_pk)
            total_occurrences = len(appearances)
            
            # Sort by lesson to find earliest appearance
            # If lesson is the same, sort by page number
            sorted_apps = sorted(appearances, key=lambda x: (x["lesson"], x["page"]))
            earliest = sorted_apps[0]
            
            lesson_num = earliest["lesson"]
            page_num = earliest["page"]
            context = earliest["context"]
            
            self.stdout.write(
                f"Lemma '{lemma.headword}' (ID: {lemma.public_id}): "
                f"occurrences={total_occurrences}, earliest_lesson={lesson_num}, page={page_num}"
            )
            
            if not dry_run:
                map_fsi_learner_metadata(
                    lemma,
                    source_locator=f"fsi_course.pdf:lesson:{lesson_num}:page:{page_num}",
                    unit=f"Lesson {lesson_num}",
                    lesson_number=lesson_num,
                    page_reference=f"p. {page_num}",
                    extracted_text=context,
                    note="Auto-tagged from FSI course corpus.",
                    occurrence_count=total_occurrences,
                    review_status="reviewed",  # Direct reviewed status
                )
                updated_count += 1

        self.style_success = self.style.SUCCESS if not dry_run else self.style.NOTICE
        self.stdout.write(self.style_success(
            f"FSI Tagging Completed. Total lemmas updated/mapped: {updated_count} (Dry-run: {dry_run})"
        ))

    def _resolve_token_to_lemma(self, token: str) -> Lemma | None:
        # Cache of already resolved tokens to optimize
        if not hasattr(self, "_token_cache"):
            self._token_cache = {}
        
        if token in self._token_cache:
            return self._token_cache[token]
        
        lemma_obj = None
        # 1. Check exact match on headword/normalized headword
        lemma_obj = Lemma.objects.filter(normalized_headword=token).first()
        if lemma_obj:
            self._token_cache[token] = lemma_obj
            return lemma_obj
        
        # 2. Check Form match
        form_obj = Form.objects.filter(normalized_form=token).select_related("lemma").first()
        if form_obj:
            self._token_cache[token] = form_obj.lemma
            return form_obj.lemma
        
        # 3. Present tense positive/negative morphology analysis fallback
        try:
            analysis = analyze_text(token, rule_set_version="fortune.verbal.slots.001")
            if analysis and analysis.get("count", 0) > 0:
                first_analysis = analysis["analyses"][0]
                lemma_public_id = first_analysis["lemma"]["public_id"]
                lemma_obj = Lemma.objects.filter(public_id=lemma_public_id).first()
                if lemma_obj:
                    self._token_cache[token] = lemma_obj
                    return lemma_obj
        except AnalysisFailure:
            pass
        except Exception:
            pass
        
        self._token_cache[token] = None
        return None
