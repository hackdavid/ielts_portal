from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from accounts.models import Role
from attempts.models import Attempt, AttemptItem
from catalog.models import (
    Exam,
    MockPack,
    MockPackItem,
    PracticeMode,
    Question,
    QuestionType,
)
from scoring.models import ScoreBreakdown
from tenancy.models import Membership, Tenant


class CatalogToScoreFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.exam = Exam.objects.get(code="PTE_ACADEMIC")
        cls.qtype = QuestionType.objects.create(
            exam=cls.exam,
            code="RA",
            name="Read Aloud",
            section="speaking",
            engine="speaking_audio",
        )
        cls.question = Question.objects.create(
            exam=cls.exam,
            question_type=cls.qtype,
            title="RA placeholder 1",
            stem={"text": "The climate of Region X is characterised by…"},
        )
        cls.user = get_user_model().objects.create_user("student", password="pass")

    def test_profile_created_for_new_users(self):
        self.assertEqual(self.user.profile.role_primary, Role.STUDENT)
        admin = get_user_model().objects.create_superuser(
            "root", "r@example.com", "pass"
        )
        self.assertEqual(admin.profile.role_primary, Role.SUPER_ADMIN)

    def test_attempt_snapshot_and_score(self):
        pack = MockPack.objects.create(
            exam=self.exam, slug="free-1", title="Free mock 1"
        )
        MockPackItem.objects.create(
            pack=pack, question=self.question, order=1, section_code="speaking"
        )
        attempt = Attempt.objects.create(
            user=self.user, exam=self.exam, pack=pack, mode=PracticeMode.FULL_MOCK
        )
        AttemptItem.objects.create(
            attempt=attempt,
            order=1,
            question=self.question,
            section_code="speaking",
            stem_snapshot=self.question.stem,
        )
        score = ScoreBreakdown.objects.create(
            attempt=attempt, scale="pte_10_90", overall=65
        )
        self.assertEqual(attempt.status, Attempt.Status.NOT_STARTED)
        self.assertIn("not official", score.disclaimer)
        self.assertEqual(attempt.items.count(), 1)

    def test_question_type_must_match_exam(self):
        other = Exam.objects.create(
            code="IELTS_AC", slug="ielts-ac", name="IELTS AC", kind="ielts"
        )
        question = Question(exam=other, question_type=self.qtype, title="Mismatch")
        with self.assertRaises(ValidationError):
            question.full_clean()

    def test_unique_question_type_code_per_exam(self):
        with self.assertRaises(IntegrityError):
            QuestionType.objects.create(
                exam=self.exam,
                code="RA",
                name="Dup",
                section="speaking",
                engine="speaking_audio",
            )

    def test_unique_membership_per_tenant(self):
        tenant = Tenant.objects.create(slug="demo", name="Demo Institute")
        Membership.objects.create(tenant=tenant, user=self.user)
        with self.assertRaises(IntegrityError):
            Membership.objects.create(tenant=tenant, user=self.user)
