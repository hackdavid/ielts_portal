"""Generate rough synthetic audio for listening questions that have no recording.

Dev/demo aid only: uses espeak-ng to read the server-side script. Replace with real
recordings by uploading an Asset and setting Question.audio in Django admin.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from catalog.models import Asset, Question, Section


class Command(BaseCommand):
    help = "Create espeak-ng audio for listening questions without Question.audio."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Regenerate all.")

    def handle(self, *args, force=False, **options):
        binary = shutil.which("espeak-ng") or shutil.which("espeak")
        if not binary:
            raise CommandError("espeak-ng is not installed (apt install espeak-ng).")
        questions = Question.objects.filter(
            question_type__section=Section.LISTENING, scorer_meta__has_key="transcript"
        )
        if not force:
            questions = questions.filter(audio__isnull=True)
        made = 0
        for question in questions:
            text = question.scorer_meta["transcript"]
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / f"{question.pk}.wav"
                subprocess.run(
                    [binary, "-v", "en-gb", "-s", "150", "-w", str(path), text],
                    check=True,
                    capture_output=True,
                )
                asset = Asset(
                    kind=Asset.Kind.AUDIO,
                    content_type="audio/wav",
                    meta={"generated": "espeak-ng", "question": str(question.pk)},
                )
                with path.open("rb") as fh:
                    asset.file.save(
                        f"listening/{question.pk}.wav", File(fh), save=False
                    )
                asset.save()
            question.audio = asset
            question.save(update_fields=["audio", "updated_at"])
            made += 1
        self.stdout.write(self.style.SUCCESS(f"Generated audio for {made} questions."))
