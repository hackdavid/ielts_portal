from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from attempts.models import Attempt
from catalog.models import Exam, QuestionType
from scoring import engines
from scoring.models import ScoreBreakdown, ScoringConfig
from scoring.services import round_overall

E = QuestionType.Engine
CFG = {
    "multi_mcq_scheme": "right_minus_wrong",
    "reorder_scheme": "adjacent_pairs",
    "wfd_scheme": "lcs_ordered",
    "ignore_articles": True,
    "enforce_word_limit": True,
}
User = get_user_model()


def det(engine, key, response, stem=None):
    return engines.deterministic(engine, stem or {}, key, response, CFG)


class EngineTests(TestCase):
    def test_mcq_single_and_tfng(self):
        self.assertEqual(det(E.MCQ_SINGLE, {"correct": "b"}, {"answer": "b"})["raw"], 1)
        self.assertEqual(det(E.MCQ_SINGLE, {"correct": "b"}, {"answer": "a"})["raw"], 0)
        key = {"answers": {"1": "TRUE", "2": "NOT GIVEN"}}
        result = det(E.TFNG, key, {"1": "true", "2": "FALSE"})
        self.assertEqual((result["raw"], result["max_raw"]), (1, 2))

    def test_mcq_multi_right_minus_wrong(self):
        key = {"correct": ["a", "c"]}
        self.assertEqual(det(E.MCQ_MULTI, key, {"answer": ["a", "c"]})["raw"], 2)
        self.assertEqual(det(E.MCQ_MULTI, key, {"answer": ["a", "b"]})["raw"], 0)
        self.assertEqual(det(E.MCQ_MULTI, key, {"answer": ["a"]})["raw"], 1)

    def test_fill_in_aliases_articles_and_word_limit(self):
        key = {"answers": {"1": ["dark green", "green"], "2": ["7", "seven"]}}
        stem = {"word_limit": 2}
        result = det(E.COMPLETION, key, {"1": "The Green.", "2": " Seven "}, stem)
        self.assertEqual(result["raw"], 2)
        one_word = det(
            E.COMPLETION,
            {"answers": {"1": ["pottery"]}},
            {"1": "the pottery"},
            {"word_limit": 1},
        )
        self.assertEqual(one_word["raw"], 1)
        too_long = det(E.COMPLETION, key, {"1": "a dark green one"}, stem)
        self.assertEqual(too_long["raw"], 0)
        dropdown = det(E.FIB_DROPDOWN, {"blanks": {"1": "beta"}}, {"1": "Beta"})
        self.assertEqual(dropdown["raw"], 1)

    def test_reorder_adjacent_pairs(self):
        key = {"order": ["p1", "p2", "p3", "p4"]}
        self.assertEqual(
            det(E.REORDER, key, {"order": ["p1", "p2", "p3", "p4"]})["raw"], 3
        )
        partial = det(E.REORDER, key, {"order": ["p3", "p4", "p1", "p2"]})
        self.assertEqual((partial["raw"], partial["max_raw"]), (2, 3))
        self.assertEqual(det(E.REORDER, key, None)["raw"], 0)

    def test_hiw_and_matching(self):
        key = {"incorrect_indices": [2, 5]}
        self.assertEqual(det(E.HIW, key, {"selected": ["2", "5"]})["raw"], 2)
        self.assertEqual(det(E.HIW, key, {"selected": ["2", "3"]})["raw"], 0)
        pairs = {"pairs": {"1": "c", "2": "a"}}
        self.assertEqual(det(E.MATCHING, pairs, {"1": "c", "2": "b"})["raw"], 1)

    def test_dictation_partial_credit(self):
        key = {"sentence": "The lecture starts at nine tomorrow"}
        full = det(E.DICTATION, key, {"answer": "the lecture starts at nine tomorrow."})
        self.assertEqual(full["scaled"], 100.0)
        mid = det(E.DICTATION, key, {"answer": "lecture starts nine"})
        self.assertEqual((mid["raw"], mid["max_raw"]), (3, 6))
        self.assertTrue(0 < mid["scaled"] < 100)

    def test_band_rounding(self):
        self.assertEqual(round_overall(6.25), 6.5)
        self.assertEqual(round_overall(6.75), 7.0)
        self.assertEqual(round_overall(6.125), 6.0)
        self.assertEqual(round_overall(6.625), 6.5)

    def test_dummy_writing_is_deterministic_and_length_aware(self):
        cfg = {"writing_traits": ["TA", "CC", "LR", "GRA"]}
        stem = {"min_words": 250}
        long = engines.dummy_writing(stem, "word " * 260, cfg, True, "x")
        short = engines.dummy_writing(stem, "word " * 40, cfg, True, "x")
        self.assertEqual(
            long, engines.dummy_writing(stem, "word " * 260, cfg, True, "x")
        )
        self.assertGreater(long["band"], short["band"])
        self.assertLessEqual(short["traits"]["TA"], 5.5)
        self.assertEqual(engines.dummy_writing(stem, "", cfg, True, "x")["band"], 0)


class AttemptScoringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.ielts = Exam.objects.get(code="IELTS_ACADEMIC")
        cls.pack = cls.ielts.mock_packs.get(slug="mock-test-1")
        cls.user = User.objects.create(username="s", email="s@example.com")
        cls.other = User.objects.create(username="o", email="o@example.com")

    def setUp(self):
        self.client.force_login(self.user)

    def start(self, pack=None, section=None):
        data = {"section": section} if section else {}
        self.client.post(
            reverse("catalog:mock_start", args=[(pack or self.pack).pk]), data
        )
        attempt = Attempt.objects.filter(user=self.user).latest("created_at")
        attempt.meta["mic_checked"] = "ok"
        attempt.save()
        return attempt

    def save(self, attempt, order, response):
        return self.client.post(
            reverse("attempts:autosave", args=[attempt.pk, order]),
            {"response": response},
            content_type="application/json",
        )

    def finish(self, attempt):
        for i in range(len(attempt.config_snapshot["sections"])):
            self.client.post(
                reverse("attempts:next_section", args=[attempt.pk]),
                {"section_index": i},
            )
        attempt.refresh_from_db()
        return attempt

    def answer_section(self, attempt, code):
        for item in attempt.items.filter(section_code=code):
            answers = {
                k: (v[0] if isinstance(v, list) else v)
                for k, v in item.answer_key_snapshot.get("answers", {}).items()
            }
            self.save(attempt, item.order, answers)

    def test_seed_creates_active_configs(self):
        self.assertTrue(
            ScoringConfig.objects.filter(exam=self.ielts, is_active=True).exists()
        )
        self.assertEqual(
            ScoringConfig.objects.filter(tenant=None).count(), Exam.objects.count()
        )

    def test_full_ielts_mock_scores_bands_and_traits(self):
        attempt = self.start()
        self.answer_section(attempt, "listening")
        attempt = self.finish(attempt)
        self.assertEqual(attempt.status, Attempt.Status.SCORED)
        breakdown = attempt.score_breakdown
        self.assertEqual(breakdown.scale, ScoreBreakdown.Scale.IELTS_BAND)
        self.assertEqual(
            set(breakdown.sections), {"listening", "reading", "writing", "speaking"}
        )
        self.assertEqual(breakdown.sections["listening"]["raw"], 40)
        self.assertEqual(breakdown.sections["listening"]["band"], 9.0)
        self.assertEqual(breakdown.sections["reading"]["band"], 0.0)
        self.assertEqual(set(breakdown.traits), {"writing", "speaking"})
        self.assertIsNotNone(breakdown.overall)
        self.assertFalse(attempt.items.filter(score_status="pending").exists())

        page = self.client.get(reverse("attempts:done", args=[attempt.pk]))
        self.assertContains(page, 'data-testid="overall"')
        self.assertContains(page, "Writing criteria")
        html = page.content.decode().replace(str(breakdown.disclaimer), "")
        self.assertNotIn("official", html.lower())

    def test_review_reveals_answers_only_after_scoring(self):
        attempt = self.start(section="listening")
        review = reverse("attempts:review", args=[attempt.pk])
        self.assertEqual(self.client.get(review).status_code, 302)
        self.save(attempt, 1, {"1": "Delgado", "2": "painting"})
        self.client.post(reverse("attempts:submit", args=[attempt.pk]))
        page = self.client.get(review)
        self.assertContains(page, "Delgado")
        self.assertContains(page, "pottery")
        self.assertContains(page, "Listening script")
        other = self.client_class()
        other.force_login(self.other)
        self.assertEqual(other.get(review).status_code, 404)

    def test_pte_mock_has_communicative_and_enabling(self):
        pack = Exam.objects.get(code="PTE_ACADEMIC").mock_packs.get(is_free=True)
        attempt = self.start(pack=pack)
        for item in attempt.items.filter(stem_snapshot___engine=E.WRITING_TEXT):
            self.save(attempt, item.order, {"text": "word " * 120})
        attempt = self.finish(attempt)
        breakdown = attempt.score_breakdown
        self.assertEqual(breakdown.scale, ScoreBreakdown.Scale.PTE_10_90)
        self.assertTrue(10 <= breakdown.overall <= 90)
        for data in breakdown.sections.values():
            self.assertTrue(10 <= data["score"] <= 90)
        self.assertIn("Grammar", breakdown.enabling)
        page = self.client.get(reverse("attempts:done", args=[attempt.pk]))
        self.assertContains(page, "Communicative skills")
        self.assertContains(page, 'data-testid="enabling"')

    @override_settings(SCORING_INLINE=False)
    def test_pending_then_worker_command_scores(self):
        attempt = self.start(section="writing")
        self.client.post(reverse("attempts:submit", args=[attempt.pk]))
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.Status.SUBMITTED)
        self.assertTrue(attempt.items.filter(score_status="pending").exists())
        self.assertContains(
            self.client.get(reverse("attempts:done", args=[attempt.pk])),
            "scoring-pending",
        )
        call_command("score_attempts", stdout=StringIO())
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.Status.SCORED)

    def test_failure_marks_failed_and_retry_works(self):
        attempt = self.start(section="reading")
        with mock.patch(
            "scoring.services._ielts_rollup", side_effect=RuntimeError("x")
        ):
            self.client.post(reverse("attempts:submit", args=[attempt.pk]))
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.Status.FAILED)
        self.assertIn("scoring_error", attempt.meta)
        self.assertContains(
            self.client.get(reverse("attempts:done", args=[attempt.pk])),
            "scoring-failed",
        )
        call_command("score_attempts", "--failed", stdout=StringIO())
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.Status.SCORED)
        self.assertNotIn("scoring_error", attempt.meta)

    def test_admin_config_change_applies_on_rescore(self):
        attempt = self.start(section="listening")
        self.answer_section(attempt, "listening")
        self.client.post(reverse("attempts:submit", args=[attempt.pk]))
        config = ScoringConfig.objects.get(exam=self.ielts, tenant=None)
        config.weights["band_tables"]["listening"] = [[0, 4.0]]
        config.version = "custom"
        config.save()
        call_command("score_attempts", "--attempt", str(attempt.pk), stdout=StringIO())
        breakdown = ScoreBreakdown.objects.get(attempt=attempt)
        self.assertEqual(breakdown.sections["listening"]["band"], 4.0)
        self.assertEqual(breakdown.config_version, "custom")

    def test_dashboard_shows_recent_score(self):
        self.user.profile.onboarded_at = self.user.date_joined
        self.user.profile.save()
        attempt = self.start(section="listening")
        self.client.post(reverse("attempts:submit", args=[attempt.pk]))
        page = self.client.get(reverse("analytics:dashboard"))
        self.assertContains(page, 'data-testid="recent-score"')
