from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.dispatch import receiver


def get_trigrams(text):
    if not text:
        return set()
    text = f"  {text.lower()}  "
    return {text[i:i+3] for i in range(len(text)-2)}


def trigram_similarity(s1, s2):
    if not s1 or not s2:
        return 0.0
    t1 = get_trigrams(str(s1))
    t2 = get_trigrams(str(s2))
    intersection = len(t1.intersection(t2))
    union = len(t1.union(t2))
    return float(intersection / union) if union > 0 else 0.0


@receiver(connection_created)
def extend_sqlite(connection, **kwargs):
    if connection.vendor == "sqlite":
        raw_conn = connection.connection
        if raw_conn is not None:
            raw_conn.create_function("similarity", 2, trigram_similarity)


class LexiconConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shona_api.lexicon"

    def ready(self):
        import shona_api.lexicon.signals

