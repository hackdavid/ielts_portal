from django.core.management.base import BaseCommand

from attempts.models import Attempt
from scoring.services import score_attempt


class Command(BaseCommand):
    help = "Score submitted attempts (worker/cron fallback and retry for failures)."

    def add_arguments(self, parser):
        parser.add_argument("--failed", action="store_true", help="Retry FAILED too.")
        parser.add_argument("--attempt", help="Score (or re-score) one attempt id.")

    def handle(self, *args, **options):
        if options["attempt"]:
            attempts = Attempt.objects.filter(pk=options["attempt"])
        else:
            statuses = [Attempt.Status.SUBMITTED, Attempt.Status.SCORING]
            if options["failed"]:
                statuses.append(Attempt.Status.FAILED)
            attempts = Attempt.objects.filter(status__in=statuses)
        done = {}
        for attempt in attempts:
            result = score_attempt(attempt, force=bool(options["attempt"]))
            done[result.status] = done.get(result.status, 0) + 1
        summary = ", ".join(f"{n} {s}" for s, n in done.items()) or "nothing to score"
        self.stdout.write(self.style.SUCCESS(f"Scoring: {summary}."))
