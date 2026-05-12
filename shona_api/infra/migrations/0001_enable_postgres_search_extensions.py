from django.db import migrations


POSTGRES_SEARCH_EXTENSIONS = ("pg_trgm", "unaccent")


def install_search_extensions(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        for extension in POSTGRES_SEARCH_EXTENSIONS:
            cursor.execute(f"CREATE EXTENSION IF NOT EXISTS {extension};")


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(
            install_search_extensions,
            reverse_code=migrations.RunPython.noop,
        )
    ]
