from django.db import migrations


def backfill(apps, schema_editor):
    Question = apps.get_model("catalog", "Question")
    Asset = apps.get_model("catalog", "Asset")
    Question.objects.filter(origin="manual").update(origin="seed")
    Asset.objects.filter(listening_questions__isnull=False).update(
        role="stimulus_audio"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0005_stimulus_asset_height_asset_model_name_asset_prompt_and_more")
    ]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
