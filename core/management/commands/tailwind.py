from django.conf import settings
from django.core.management.base import BaseCommand
from pytailwindcss import run

TAILWIND_VERSION = "v4.3.3"


class Command(BaseCommand):
    help = (
        "Build static/css/app.css from static/src/tailwind.css (pinned Tailwind CLI)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true", help="Rebuild on change.")

    def handle(self, *args, watch=False, **options):
        cli_args = ["-i", "static/src/tailwind.css", "-o", "static/css/app.css"]
        cli_args.append("--watch" if watch else "--minify")
        run(
            cli_args,
            cwd=settings.BASE_DIR,
            auto_install=True,
            version=TAILWIND_VERSION,
            live_output=True,
        )
