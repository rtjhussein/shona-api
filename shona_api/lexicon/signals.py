from django.db.models.signals import post_save
from django.dispatch import receiver
from shona_api.editorial.models import ReviewState
from .models import Lemma
from .learner_metadata import apply_rule_based_curriculum_tags

@receiver(post_save, sender=Lemma)
def trigger_pedagogical_tagging(sender, instance, created, **kwargs):
    # Only run rule-based curriculum matching if the lemma is currently published
    if instance.review_state == ReviewState.PUBLISHED:
        # Check if the lemma is already tagged by rule match to prevent infinite recursion
        source_locator = "curriculum_notes_forms_1_4.pdf:rule_match"
        has_rule_link = any(link.get("source_locator") == source_locator for link in instance.learner_source_links)
        
        if not has_rule_link:
            apply_rule_based_curriculum_tags(instance)
