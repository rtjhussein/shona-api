from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("extraction", "0004_ingestionrun_precompiled_jsonl"),
    ]

    operations = [
        migrations.AddField(
            model_name="ingestionrun",
            name="skip_duplicates",
            field=models.BooleanField(default=True),
        ),
    ]
