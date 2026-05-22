from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lexicon", "0003_lemma_communication_contexts_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="tonerecord",
            name="dialects",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
