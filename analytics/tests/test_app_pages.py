from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.services import get_profile
from attempts.models import Attempt
from catalog.models import Exam
from scoring.models import ScoreBreakdown
from tenancy.models import AccessInvite, Membership, Tenant

User = get_user_model()


def make_user(email, tenant=None, role=Membership.Role.STUDENT):
    user = User.objects.create_user(username=email, email=email)
    profile = get_profile(user)
    profile.onboarded_at = timezone.now()
    profile.save()
    if tenant:
        Membership.objects.create(
            tenant=tenant,
            user=user,
            role=role,
            is_active=True,
            joined_at=timezone.now(),
        )
    return user


class StudentAppTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        cls.exam = Exam.objects.get(code="IELTS_ACADEMIC")
        cls.student = make_user("s@example.com")

    def setUp(self):
        self.client.force_login(self.student)

    def scored(self, qtype, raw):
        attempt = Attempt.objects.create(
            user=self.student,
            exam=self.exam,
            mode="question",
            status=Attempt.Status.SCORED,
            submitted_at=timezone.now(),
        )
        ScoreBreakdown.objects.create(
            attempt=attempt,
            overall=6.5,
            scale=ScoreBreakdown.Scale.IELTS_BAND,
            sections={"reading": {"band": 6.5, "raw": raw, "max_raw": 10}},
            items_summary=[
                {
                    "order": 1,
                    "section": "reading",
                    "qtype": qtype,
                    "raw": raw,
                    "max_raw": 10,
                    "scaled": raw * 10,
                    "band": None,
                    "scorer": "det",
                }
            ],
        )
        return attempt

    def test_new_student_is_pointed_at_a_mock(self):
        page = self.client.get(reverse("analytics:dashboard"))
        self.assertContains(page, 'data-testid="next-step"')
        self.assertContains(page, "Find your level")
        self.assertContains(
            page, "Your skill map appears after your first scored attempt"
        )

    def test_next_step_targets_weakest_question_type(self):
        codes = list(
            self.exam.question_types.filter(section="reading").values_list(
                "code", flat=True
            )[:2]
        )
        self.scored(codes[0], 9)
        self.scored(codes[1], 2)
        page = self.client.get(reverse("analytics:dashboard"))
        weakest = self.exam.question_types.get(code=codes[1])
        self.assertContains(page, "Your next step")
        self.assertContains(
            page, reverse("catalog:qtype_list", args=[self.exam.slug, weakest.code])
        )
        self.assertContains(page, "20%")
        self.assertContains(page, 'data-testid="skill-map"')

    def test_results_history_lists_own_attempts_only(self):
        mine = self.scored("R_TFNG", 5)
        other = make_user("o@example.com")
        theirs = Attempt.objects.create(user=other, exam=self.exam, mode="question")
        page = self.client.get(reverse("analytics:results"))
        self.assertContains(page, reverse("attempts:done", args=[mine.pk]))
        self.assertNotContains(page, str(theirs.pk))
        self.assertContains(page, "Band 6.5")

    def test_app_shell_navigation_marks_current_page(self):
        page = self.client.get(reverse("catalog:exam_list"))
        self.assertContains(page, 'aria-label="App tabs"')
        self.assertContains(page, "Mock tests")
        self.assertContains(page, 'aria-current="page"')


class OrgAppTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="Acme Institute", slug="acme", seat_limit=10
        )
        cls.other_tenant = Tenant.objects.create(name="Other", slug="other")
        cls.org = make_user("admin@acme.test", cls.tenant, Membership.Role.ORG)
        cls.student = make_user("kid@acme.test", cls.tenant)
        cls.outsider = make_user("kid@other.test", cls.other_tenant)
        AccessInvite.objects.create(
            tenant=cls.tenant, email="new@acme.test", role="student"
        )

    def setUp(self):
        self.client.force_login(self.org)

    def test_org_pages_render(self):
        for name in ("institute:console", "institute:students", "institute:access"):
            with self.subTest(name=name):
                page = self.client.get(reverse(name))
                self.assertContains(page, "Acme Institute")
        self.assertContains(
            self.client.get(reverse("institute:students")), "kid@acme.test"
        )
        self.assertContains(
            self.client.get(reverse("institute:access")), "new@acme.test"
        )

    def test_student_search(self):
        page = self.client.get(reverse("institute:students"), {"q": "nobody"})
        self.assertNotContains(page, "kid@acme.test")

    def test_student_detail_is_scoped_to_own_org(self):
        ok = self.client.get(
            reverse("institute:student_detail", args=[self.student.pk])
        )
        self.assertContains(ok, "kid@acme.test")
        other = self.client.get(
            reverse("institute:student_detail", args=[self.outsider.pk])
        )
        self.assertEqual(other.status_code, 404)

    def test_students_cannot_open_org_pages(self):
        self.client.force_login(self.student)
        for name in ("institute:students", "institute:access"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)
