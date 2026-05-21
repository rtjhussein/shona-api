import os
import django
from django.db import transaction

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.extraction.services import publish_reviewed_extraction_unit, ExtractionUnitPublishError
from shona_api.lexicon.models import Lemma, Sense, ToneRecord, Form


def main():
    print("Fetching imported Gemini extraction units...")
    units = ExtractionUnit.objects.filter(
        parser_name="gemini-2.5-flash-v1",
        review_state=ReviewState.NEEDS_REVIEW
    )
    
    count = units.count()
    print(f"Found {count} units to publish.")
    
    if count == 0:
        print("No units to process. Have they already been published?")
        return

    published_count = 0
    failed_count = 0

    print("Promoting extraction units to canonical models...")
    for idx, unit in enumerate(units.order_by('source_location_reference'), start=1):
        print(f"[{idx}/{count}] Processing {unit.source_location_reference}...")
        try:
            with transaction.atomic():
                # Set review state to APPROVED so it is publishable
                unit.review_state = ReviewState.APPROVED
                unit.save()
                
                # Publish the unit
                bundle = publish_reviewed_extraction_unit(unit)
                
                print(f"  SUCCESS! Promoted to Lemma: {bundle.lemma} (ID: {bundle.lemma.public_id})")
                print(f"    Senses: {len(bundle.senses)}")
                print(f"    Tone Records: {len(bundle.tone_records)}")
                print(f"    Forms: {len(bundle.forms)}")
                published_count += 1
        except Exception as e:
            failed_count += 1
            print(f"  FAILED to publish {unit.source_location_reference}: {e}")

    print("\n" + "="*50)
    print(f"PUBLISHING SUMMARY:")
    print(f"  Total processed: {count}")
    print(f"  Successfully published: {published_count}")
    print(f"  Failed: {failed_count}")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()
