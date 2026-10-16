"""Backfill content_hash / minhash / embeddings for the existing question bank."""

from django.core.management.base import BaseCommand

from catalog.models import Question
from content.dedup import index_question


class Command(BaseCommand):
    help = "Index existing questions for duplicate detection."

    def add_arguments(self, parser):
        parser.add_argument("--no-embed", action="store_true")
        parser.add_argument("--all", action="store_true", help="Re-index everything.")

    def handle(self, *args, no_embed=False, all=False, **options):
        qs = Question.objects.select_related("question_type", "stimulus")
        if not all:
            qs = qs.filter(content_hash="")
        n = 0
        for question in qs.iterator():
            index_question(question, embed=not no_embed)
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Indexed {n} questions."))
