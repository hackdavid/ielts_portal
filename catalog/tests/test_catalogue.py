from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Exam, MockPack, MockPackSection, Question, QuestionType
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
        for code in ("PTE_ACADEMIC", "PTE_CORE"):
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


class IeltsSeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def test_ielts_mocks_follow_real_structure_and_timing(self):
        for code in ("IELTS_ACADEMIC", "IELTS_GENERAL"):
            exam = Exam.objects.get(code=code)
            pack = exam.mock_packs.get(slug="mock-test-1", is_free=True)
            with self.subTest(code):
                self.assertFalse(
                    Question.objects.filter(
                        exam=exam, title__startswith="Demo "
                    ).exists()
                )
                plan = pack.section_plan()
                self.assertEqual(
                    [(r["section"], r["duration_sec"]) for r in plan],
                    [
                        ("listening", 1800),
                        ("reading", 3600),
                        ("writing", 3600),
                        ("speaking", 840),
                    ],
                )
                totals = {}
                for item in pack.items.select_related("question"):
                    n = len(item.question.stem.get("items", [])) or 1
                    totals[item.section_code] = totals.get(item.section_code, 0) + n
                self.assertEqual(
                    totals,
                    {"listening": 40, "reading": 40, "writing": 2, "speaking": 3},
                )
                numbers = [
                    i["n"]
                    for item in pack.items.filter(section_code="reading").order_by(
                        "order"
                    )
                    for i in item.question.stem["items"]
                ]
                self.assertEqual(numbers, list(range(1, 41)))
                for qtype in exam.question_types.all():
                    self.assertTrue(qtype.questions.exists(), qtype.code)
                    self.assertTrue(qtype.default_time_sec)

    def test_admin_timing_edits_survive_reseed_and_pack_override(self):
        exam = Exam.objects.get(code="IELTS_ACADEMIC")
        exam.section_timings.filter(section="reading").update(duration_sec=3000)
        qtype = exam.question_types.get(code="TASK2")
        qtype.default_time_sec = 2000
        qtype.save()
        call_command("seed_demo", stdout=StringIO())
        pack = exam.mock_packs.get(slug="mock-test-1")
        self.assertEqual(pack.section_plan()[1]["duration_sec"], 3000)
        qtype.refresh_from_db()
        self.assertEqual(qtype.default_time_sec, 2000)
        MockPackSection.objects.create(
            pack=pack, section="writing", order=0, duration_sec=1800
        )
        MockPackSection.objects.create(pack=pack, section="speaking", order=1)
        self.assertEqual(
            pack.section_plan(),
            [
                {
                    "section": "writing",
                    "duration_sec": 1800,
                    "extra_sec": 0,
                    "is_override": True,
                },
                {
                    "section": "speaking",
                    "duration_sec": 840,
                    "extra_sec": 0,
                    "is_override": False,
                },
            ],
        )

    def test_dashboard_shows_mocks_and_practice_without_answers(self):
        user = User.objects.create(username="d", email="d@example.com")
        user.profile.onboarded_at = timezone.now()
        user.profile.save()
        self.client.force_login(user)
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertContains(response, "IELTS Academic Mock Test 1")
        self.assertContains(response, "True / False / Not Given")
        self.assertNotIn("tenfold", response.content.decode())
        pack = Exam.objects.get(code="IELTS_ACADEMIC").mock_packs.get(
            slug="mock-test-1"
        )
        detail = self.client.get(
            reverse("catalog:mock_detail", args=[pack.pk])
        ).content.decode()
        self.assertIn("60 min", detail)
        self.assertNotIn("Delgado", detail)
