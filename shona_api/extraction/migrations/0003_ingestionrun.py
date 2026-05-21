from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("extraction", "0002_add_batch_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="IngestionRun",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("batch_id", models.CharField(db_index=True, max_length=120)),
                ("start_page", models.PositiveIntegerField()),
                ("end_page", models.PositiveIntegerField()),
                ("parser_repo_path", models.CharField(max_length=500)),
                ("pdf_path", models.CharField(max_length=500)),
                ("output_dir", models.CharField(max_length=500)),
                ("jsonl_path", models.CharField(blank=True, max_length=500)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("dry_run", models.BooleanField(default=False)),
                ("overwrite_pages", models.BooleanField(default=False)),
                ("auto_publish", models.BooleanField(default=False)),
                ("imported_count", models.PositiveIntegerField(default=0)),
                ("duplicate_count", models.PositiveIntegerField(default=0)),
                ("publishable_count", models.PositiveIntegerField(default=0)),
                ("published_count", models.PositiveIntegerField(default=0)),
                ("failed_publish_count", models.PositiveIntegerField(default=0)),
                ("log_text", models.TextField(blank=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="hannan_ingestion_runs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="ingestionrun",
            index=models.Index(fields=["status", "created_at"], name="ingrun_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="ingestionrun",
            index=models.Index(fields=["batch_id", "created_at"], name="ingrun_batch_created_idx"),
        ),
    ]
