from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from attempts.models import Attempt
from catalog.models import Exam, PracticeMode, Question

User = get_user_model()


class PlayerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.exam = Exam.objects.get(code="IELTS_ACADEMIC")
        cls.pack = cls.exam.mock_packs.get(slug="mock-test-1")
        cls.user = User.objects.create(username="s", email="s@example.com")
        cls.other = User.objects.create(username="o", email="o@example.com")

    def setUp(self):
        self.client.force_login(self.user)

    def start(self, section=None, pack=None):
        data = {"section": section} if section else {}
        url = reverse("catalog:mock_start", args=[(pack or self.pack).pk])
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        return Attempt.objects.filter(user=self.user).latest("created_at"), response

    def save(self, attempt, order, response, client=None):
        return (client or self.client).post(
            reverse("attempts:autosave", args=[attempt.pk, order]),
            {"response": response},
            content_type="application/json",
        )

    def play(self, attempt):
        attempt.meta["mic_checked"] = "ok"
        attempt.save()
        return self.client.get(reverse("attempts:play", args=[attempt.pk]))

    def test_start_snapshots_pack_and_resumes(self):
        attempt, response = self.start()
        self.assertRedirects(
            response,
            reverse("attempts:play", args=[attempt.pk]),
            target_status_code=302,
        )
        self.assertEqual(attempt.mode, PracticeMode.FULL_MOCK)
        self.assertEqual(attempt.items.count(), self.pack.items.count())
        self.assertEqual(
            [s["section"] for s in attempt.config_snapshot["sections"]],
            ["listening", "reading", "writing", "speaking"],
        )
        first = attempt.items.get(order=1)
        Question.objects.filter(pk=first.question_id).update(stem={"changed": True})
        first.refresh_from_db()
        self.assertNotIn("changed", first.stem_snapshot)
        again, _ = self.start()
        self.assertEqual(again.pk, attempt.pk)
        self.assertEqual(Attempt.objects.filter(user=self.user).count(), 1)

    def test_mic_check_gate_then_player_hides_answers(self):
        attempt, _ = self.start()
        play = reverse("attempts:play", args=[attempt.pk])
        self.assertRedirects(
            self.client.get(play), reverse("attempts:mic_check", args=[attempt.pk])
        )
        self.client.post(
            reverse("attempts:mic_check", args=[attempt.pk]), {"result": "skipped"}
        )
        html = self.client.get(play).content.decode()
        self.assertIn('data-testid="timer"', html)
        for secret in ("Delgado", "answer_key", "transcript", "pottery"):
            self.assertNotIn(secret, html)
        self.assertEqual(
            html.count('data-testid="item"'),
            attempt.items.filter(section_code="listening").count(),
        )

    def test_autosave_restores_and_clock_matches_server(self):
        attempt, _ = self.start()
        self.assertEqual(self.save(attempt, 1, {"1": "Delgado"}).json()["ok"], True)
        html = self.play(attempt).content.decode()
        self.assertIn('value="Delgado"', html)
        state = self.client.get(reverse("attempts:state", args=[attempt.pk])).json()
        attempt.refresh_from_db()
        expected = attempt.started_at + timedelta(seconds=1800 + 120)
        self.assertLess(abs(state["deadline_ms"] / 1000 - expected.timestamp()), 2)
        self.assertLess(
            abs(state["server_now_ms"] / 1000 - timezone.now().timestamp()), 2
        )

    def test_autosave_rejects_other_users_closed_sections_and_late_saves(self):
        attempt, _ = self.start()
        other = self.client_class()
        other.force_login(self.other)
        self.assertEqual(
            self.save(attempt, 1, {"1": "x"}, client=other).status_code, 404
        )
        reading = attempt.items.filter(section_code="reading").first()
        self.assertEqual(self.save(attempt, reading.order, {"1": "x"}).status_code, 409)
        self.assertEqual(self.save(attempt, 1, "bad").status_code, 400)
        attempt.server_deadline_at = timezone.now() - timedelta(seconds=6)
        attempt.save()
        response = self.save(attempt, 1, {"1": "late"})
        self.assertEqual(response.json()["code"], "section_closed")
        attempt.refresh_from_db()
        self.assertEqual(attempt.meta["section_index"], 1)
        self.assertEqual(
            self.save(attempt, reading.order, {"1": "ok"}).status_code, 200
        )

    def test_sections_advance_and_double_finalize_is_idempotent(self):
        attempt, _ = self.start()
        for i in range(4):
            self.client.post(
                reverse("attempts:next_section", args=[attempt.pk]),
                {"section_index": i},
            )
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.Status.SCORED)
        stamp = attempt.submitted_at
        response = self.client.post(reverse("attempts:submit", args=[attempt.pk]))
        self.assertRedirects(response, reverse("attempts:done", args=[attempt.pk]))
        attempt.refresh_from_db()
        self.assertEqual(attempt.submitted_at, stamp)
        self.assertContains(
            self.client.get(reverse("attempts:done", args=[attempt.pk])),
            "Practice results",
        )
        self.assertEqual(self.save(attempt, 1, {"1": "x"}).status_code, 409)
        # stale double-click on "Finish section" must not skip a section
        fresh, _ = self.start()
        url = reverse("attempts:next_section", args=[fresh.pk])
        self.client.post(url, {"section_index": 0})
        self.client.post(url, {"section_index": 0})
        fresh.refresh_from_db()
        self.assertEqual(fresh.meta["section_index"], 1)

    def test_expired_attempt_auto_submits(self):
        attempt, _ = self.start()
        attempt.server_deadline_at = timezone.now() - timedelta(hours=5)
        attempt.save()
        response = self.client.get(reverse("attempts:play", args=[attempt.pk]))
        self.assertRedirects(response, reverse("attempts:done", args=[attempt.pk]))

    def test_speaking_upload_is_playable_by_owner_only(self):
        attempt, _ = self.start(section="speaking")
        self.assertEqual(attempt.mode, PracticeMode.SECTION)
        self.assertEqual(
            set(attempt.items.values_list("section_code", flat=True)), {"speaking"}
        )
        order = attempt.items.first().order
        url = reverse("attempts:audio", args=[attempt.pk, order])
        empty = SimpleUploadedFile("a.webm", b"", content_type="audio/webm")
        self.assertEqual(self.client.post(url, {"audio": empty}).status_code, 400)
        text = SimpleUploadedFile("a.txt", b"hello", content_type="text/plain")
        self.assertEqual(self.client.post(url, {"audio": text}).status_code, 415)
        audio = SimpleUploadedFile(
            "a.webm", b"\x1aE\xdf\xa3webm", content_type="audio/webm;codecs=opus"
        )
        data = self.client.post(url, {"audio": audio}).json()
        self.assertTrue(data["ok"])
        played = self.client.get(data["url"])
        self.assertEqual(played["Content-Type"], "audio/webm")
        self.assertEqual(b"".join(played.streaming_content), b"\x1aE\xdf\xa3webm")
        other = self.client_class()
        other.force_login(self.other)
        self.assertEqual(other.get(data["url"]).status_code, 404)

    def test_listening_play_count_limit(self):
        attempt, _ = self.start(section="listening")
        url = reverse("attempts:play_count", args=[attempt.pk, 1])
        self.assertEqual(self.client.post(url).json()["play_count"], 1)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(attempt.items.get(order=1).response_flags["play_count"], 1)
        self.assertFalse(attempt.config_snapshot["listening"]["allow_seek"])

    def test_question_wise_practice(self):
        qtype = self.exam.question_types.get(code="R_TFNG")
        url = reverse("catalog:practice_start", args=[self.exam.slug, qtype.code])
        self.client.post(url)
        attempt = Attempt.objects.get(user=self.user)
        self.assertEqual(attempt.mode, PracticeMode.QUESTION)
        self.assertEqual(attempt.items.count(), qtype.questions.count())
        self.assertEqual(
            attempt.duration_sec, qtype.default_time_sec * qtype.questions.count()
        )
        one = qtype.questions.first()
        self.client.post(url, {"question": one.pk})
        single = Attempt.objects.filter(user=self.user).latest("created_at")
        self.assertEqual(
            list(single.items.values_list("question", flat=True)), [one.pk]
        )
        self.client.post(url, {"question": "not-a-uuid"})
        self.assertEqual(Attempt.objects.filter(user=self.user).count(), 2)
        html = self.play(single).content.decode()
        self.assertIn("TRUE", html)

    def test_locked_pack_cannot_start(self):
        pte = Exam.objects.get(code="PTE_ACADEMIC")
        paid = pte.mock_packs.get(is_free=False)
        response = self.client.post(reverse("catalog:mock_start", args=[paid.pk]))
        self.assertRedirects(
            response, reverse("plans:locked"), fetch_redirect_response=False
        )
        self.assertFalse(Attempt.objects.exists())

    def test_every_free_mock_section_renders(self):
        for pack in [self.pack] + [
            Exam.objects.get(code=c).mock_packs.get(is_free=True)
            for c in ("IELTS_GENERAL", "PTE_ACADEMIC", "PTE_CORE")
        ]:
            attempt, _ = self.start(pack=pack)
            for index in range(len(attempt.config_snapshot["sections"])):
                with self.subTest(pack=pack.title, section=index):
                    response = self.play(attempt)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotIn("answer_key", response.content.decode())
                    self.client.post(
                        reverse("attempts:next_section", args=[attempt.pk]),
                        {"section_index": index},
                    )
                    attempt.refresh_from_db()
            self.assertEqual(attempt.status, Attempt.Status.SCORED)

    def test_blank_autosave_is_not_answered(self):
        attempt, _ = self.start(section="listening")
        self.save(attempt, 1, {"1": "", "2": "  ", "3": []})
        self.client.post(reverse("attempts:submit", args=[attempt.pk]))
        response = self.client.get(reverse("attempts:done", args=[attempt.pk]))
        self.assertContains(response, "Answered 0 of")

    def test_dev_media_hides_recordings(self):
        from django.http import Http404
        from django.test import RequestFactory

        from core.views import dev_media

        with self.assertRaises(Http404):
            dev_media(RequestFactory().get("/"), "assets/2026/10/recordings/x.webm")

    def test_dashboard_lists_attempts(self):
        self.user.profile.onboarded_at = timezone.now()
        self.user.profile.save()
        attempt, _ = self.start()
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertContains(response, reverse("attempts:play", args=[attempt.pk]))


class ExamShellTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.user = User.objects.create(username="x", email="x@example.com")

    def setUp(self):
        self.client.force_login(self.user)

    def open(self, exam_code, section=None, slug=None):
        exam = Exam.objects.get(code=exam_code)
        pack = exam.mock_packs.get(slug=slug) if slug else exam.mock_packs.first()
        data = {"section": section} if section else {}
        self.client.post(reverse("catalog:mock_start", args=[pack.pk]), data)
        attempt = Attempt.objects.filter(user=self.user).latest("created_at")
        attempt.meta["mic_checked"] = "ok"
        attempt.save()
        return self.client.get(reverse("attempts:play", args=[attempt.pk]))

    def test_ielts_listening_has_intro_flags_and_per_question_navigator(self):
        html = self.open("IELTS_ACADEMIC", "listening", "mock-test-1").content.decode()
        self.assertIn('data-testid="section-intro"', html)
        self.assertIn('data-testid="navigator"', html)
        self.assertIn('data-nav="1:', html)
        self.assertIn("Flag question", html)
        self.assertIn("linear: false", html)

    def test_reading_splits_passage_into_paragraphs(self):
        html = self.open("IELTS_ACADEMIC", "reading", "mock-test-1").content.decode()
        self.assertIn('data-testid="passage"', html)
        self.assertIn('<p class="mb-4 last:mb-0">', html)
        self.assertIn("exam-divider", html)

    def test_pte_full_mock_is_linear(self):
        html = self.open("PTE_ACADEMIC").content.decode()
        self.assertIn('data-exam="pte"', html)
        self.assertIn("linear: true", html)

    def test_catalogue_shows_format_guides(self):
        html = self.client.get(
            reverse("catalog:qtype_list", args=["ielts-academic", "R_TFNG"])
        ).content.decode()
        self.assertIn('data-testid="qtype-guide"', html)
        self.assertIn("Not Given", html)
        detail = self.client.get(
            reverse("catalog:exam_detail", args=["ielts-academic"])
        )
        self.assertContains(detail, "Band 0–9 in half bands")


class ExamGuidePageTests(TestCase):
    def test_public_exam_guide_lists_formats(self):
        call_command("seed_demo", stdout=StringIO())
        response = self.client.get(reverse("pages:exam_guide"))
        self.assertContains(response, 'data-testid="guide-exam"', count=4)
        self.assertContains(response, "True / False / Not Given")
        self.assertContains(response, "Write from Dictation")
