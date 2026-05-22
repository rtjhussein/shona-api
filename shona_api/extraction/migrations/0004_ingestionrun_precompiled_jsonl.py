from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("extraction", "0003_ingestionrun"),
    ]

    operations = [
        migrations.AddField(
            model_name="ingestionrun",
            name="run_kind",
            field=models.CharField(
                choices=[
                    ("gemini_pipeline", "Gemini pipeline"),
                    ("precompiled_jsonl", "Precompiled JSONL"),
                ],
                db_index=True,
                default="gemini_pipeline",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="ingestionrun",
            name="source_jsonl_path",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="ingestionrun",
            name="import_parser_name",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="ingestionrun",
            name="auto_approve",
            field=models.BooleanField(default=False),
        ),
    ]
