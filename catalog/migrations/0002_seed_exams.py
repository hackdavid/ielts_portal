from django.db import migrations

EXAMS = [
    ("PTE_ACADEMIC", "pte-academic", "PTE Academic", "pte"),
    ("PTE_CORE", "pte-core", "PTE Core", "pte"),
    ("IELTS_ACADEMIC", "ielts-academic", "IELTS Academic", "ielts"),
    ("IELTS_GENERAL", "ielts-general", "IELTS General", "ielts"),
]


def seed_exams(apps, schema_editor):
    Exam = apps.get_model("catalog", "Exam")
    for code, slug, name, kind in EXAMS:
        Exam.objects.get_or_create(
            code=code, defaults={"slug": slug, "name": name, "kind": kind}
        )


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]

    operations = [migrations.RunPython(seed_exams, migrations.RunPython.noop)]
