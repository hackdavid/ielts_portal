"""Download the Piper voice used for generated listening audio (≈77 MB, once)."""

from django.core.management.base import BaseCommand

from content.media import tts


class Command(BaseCommand):
    help = "Fetch the Piper TTS voice into CONTENT_TTS_DIR and test it."

    def handle(self, *args, **options):
        path = tts.download_voice()
        data, ctype, _, ms, provider, model, _ = tts.synthesize(
            [{"speaker": "A", "text": "Piper voice is ready."}]
        )
        self.stdout.write(
            self.style.SUCCESS(f"{path} → {provider}/{model}: {ms} ms {ctype}")
        )
