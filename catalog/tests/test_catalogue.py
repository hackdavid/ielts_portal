from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Exam, MockPack, Question, QuestionType
from plans.models import Entitlement
from tenancy.models import Membership, Tenant

User = get_user_model()
SENTINEL = "ANSWER-SENTINEL-9f3c"


class SeedDemoTests(TestCase):
    def test_seed_is_idempotent_and_meets_phase2_acceptance(self):
        call_command("seed_demo", stdout=StringIO())
        counts = (
            Question.objects.count(),
            MockPack.objects.count(),
            QuestionType.objects.count(),
        )
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(
            counts,
            (
                Question.objects.count(),
                MockPack.objects.count(),
                QuestionType.objects.count(),
            ),
        )
        for code in ("PTE_ACADEMIC", "IELTS_ACADEMIC", "PTE_CORE", "IELTS_GENERAL"):
            exam = Exam.objects.get(code=code)
            with self.subTest(code):
                self.assertTrue(exam.mock_packs.filter(is_free=True).exists())
                self.assertTrue(exam.mock_packs.filter(is_free=False).exists())
                for qtype in exam.question_types.all():
                    self.assertGreaterEqual(qtype.questions.count(), 3, qtype)
                for pack in exam.mock_packs.all():
                    self.assertEqual(pack.items.count(), exam.question_types.count())
                    self.assertFalse(pack.items.exclude(question__exam=exam).exists())
        engines = set(QuestionType.objects.values_list("engine", flat=True))
        self.assertTrue(set(QuestionType.Engine.values) <= engines | {"other"})
        for question in Question.objects.all()[:50]:
            question.full_clean()


class CatalogueViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.user = User.objects.create(username="s", email="s@example.com")
        cls.exam = Exam.objects.get(code="PTE_ACADEMIC")
        cls.free = cls.exam.mock_packs.get(is_free=True)
        cls.paid = cls.exam.mock_packs.get(is_free=False)
        cls.qtype = cls.exam.question_types.get(code="RO")
        Question.objects.filter(exam=cls.exam).update(answer_key={"secret": SENTINEL})

    def setUp(self):
        self.client.force_login(self.user)

    def urls(self):
        slug = self.exam.slug
        return [
            reverse("catalog:exam_list"),
            reverse("catalog:exam_detail", args=[slug]),
            reverse("catalog:exam_detail", args=[slug]) + "?tab=types",
            reverse("catalog:qtype_list", args=[slug, self.qtype.code]),
            reverse("catalog:mock_list", args=[slug]),
            reverse("catalog:mock_detail", args=[self.free.pk]),
            reverse("catalog:mock_detail", args=[self.paid.pk]),
        ]

    def test_login_required_everywhere(self):
        self.client.logout()
        for url in self.urls() + [reverse("plans:locked")]:
            with self.subTest(url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(
                    response["Location"].startswith(reverse("accounts:login"))
                )

    def test_pages_render_without_answer_keys(self):
        for url in self.urls():
            with self.subTest(url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertNotIn(SENTINEL, html)
                self.assertNotIn("answer_key", html)

    def test_qtype_filters(self):
        url = reverse("catalog:qtype_list", args=[self.exam.slug, self.qtype.code])
        self.assertEqual(len(self.client.get(url).context["questions"]), 3)
        predicted = self.client.get(url, {"prediction": "1"}).context["questions"]
        self.assertTrue(predicted and all(q.is_prediction for q in predicted))
        self.assertEqual(
            len(self.client.get(url, {"difficulty": "2"}).context["questions"]), 1
        )
        self.assertEqual(
            len(self.client.get(url, {"topic": "education"}).context["questions"]), 1
        )
        for bogus in (
            {"difficulty": "abc"},
            {"prediction": "x"},
            {"topic": "nope"},
            {"difficulty": "99"},
        ):
            with self.subTest(bogus):
                self.assertEqual(self.client.get(url, bogus).status_code, 200)
        self.assertEqual(
            self.client.get(
                reverse("catalog:qtype_list", args=[self.exam.slug, "NOPE"])
            ).status_code,
            404,
        )

    def test_free_filter_on_mock_list(self):
        url = reverse("catalog:mock_list", args=[self.exam.slug])
        packs = self.client.get(url, {"free": "1"}).context["packs"]
        self.assertEqual([p.pk for p in packs], [self.free.pk])

    def test_locked_and_free_start(self):
        self.assertContains(
            self.client.get(reverse("catalog:mock_detail", args=[self.paid.pk])),
            "Locked",
        )
        locked = self.client.post(reverse("catalog:mock_start", args=[self.paid.pk]))
        self.assertRedirects(locked, reverse("plans:locked"))
        free = self.client.post(reverse("catalog:mock_start", args=[self.free.pk]))
        self.assertEqual(free.status_code, 501)
        self.assertEqual(
            self.client.get(
                reverse("catalog:mock_start", args=[self.free.pk])
            ).status_code,
            405,
        )

    def test_entitlement_unlocks_pack(self):
        Entitlement.objects.create(user=self.user, key=f"pack:{self.paid.pk}")
        self.assertEqual(
            self.client.post(
                reverse("catalog:mock_start", args=[self.paid.pk])
            ).status_code,
            501,
        )
        Entitlement.objects.all().update(
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )
        self.assertRedirects(
            self.client.post(reverse("catalog:mock_start", args=[self.paid.pk])),
            reverse("plans:locked"),
        )

    def test_org_entitlement_and_org_only_content(self):
        org = Tenant.objects.create(slug="acme", name="Acme")
        private = MockPack.objects.create(
            exam=self.exam, tenant=org, slug="acme-1", title="Acme mock"
        )
        url = reverse("catalog:mock_detail", args=[private.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        Membership.objects.create(tenant=org, user=self.user, role="student")
        self.assertEqual(self.client.get(url).status_code, 200)
        Entitlement.objects.create(tenant=org, key="unlimited", source="institute")
        self.assertEqual(
            self.client.post(
                reverse("catalog:mock_start", args=[self.paid.pk])
            ).status_code,
            501,
        )
