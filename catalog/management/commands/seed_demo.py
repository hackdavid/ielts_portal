from django.core.management.base import BaseCommand

from catalog.demo import seed
from scoring.services import ensure_default_configs


class Command(BaseCommand):
    help = "Create/refresh the placeholder demo catalogue (safe to re-run)."

    def handle(self, *args, **options):
        counts = seed()
        counts["scoring_configs"] = ensure_default_configs()
        summary = ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in counts.items())
        self.stdout.write(self.style.SUCCESS(f"Demo catalogue ready: {summary}."))
