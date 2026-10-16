"""Worker: run queued GenerationJobs (use when CONTENT_JOBS_INLINE=0)."""

import time

from django.core.management.base import BaseCommand

from content.models import GenerationJob
from content.pipeline import run_job


class Command(BaseCommand):
    help = "Run queued content-generation jobs."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Drain and exit.")
        parser.add_argument("--job", type=int, help="Run (or re-run) one job id.")
        parser.add_argument("--sleep", type=int, default=5)

    def handle(self, *args, once=False, job=None, sleep=5, **options):
        if job:
            self._run(GenerationJob.objects.get(pk=job))
            return
        while True:
            queued = GenerationJob.objects.filter(status=GenerationJob.Status.QUEUED)
            picked = queued.order_by("created_at").first()
            if picked and queued.filter(pk=picked.pk).update(
                status=GenerationJob.Status.RUNNING
            ):
                self._run(picked)
                continue
            if once:
                return
            time.sleep(sleep)

    def _run(self, job):
        self.stdout.write(f"Running {job} …")
        job = run_job(job)
        drafts = job.drafts.count()
        self.stdout.write(f"  → {job.get_status_display()} ({drafts} drafts)")
