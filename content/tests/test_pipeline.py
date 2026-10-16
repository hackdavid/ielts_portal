import io
import wave
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase, override_settings

from attempts.models import QuestionExposure
from attempts.services import questions_for, record_exposure, unseen_first
from catalog.models import Exam, MockPack, MockPackItem, PracticeMode, Question
from catalog.models import QuestionType as QT
from content import contracts as C
from content import dedup
from content.models import DraftQuestion, GenerationJob, SimilarityHit, SourceDocument
from content.pipeline import analyse_document, check_duplicates, run_job
from content.publish import PublishError, blockers, publish


def _tone(text, speaker):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\0\0" * 1600 * (1 + len(text) // 40))
    return buf.getvalue()


@override_settings(
    CONTENT_LLM_API_KEY="",
    GEMINI_API_KEY="",
    CONTENT_TTS_ENABLED=False,
    CONTENT_ALLOW_MOCK_PUBLISH="1",
)
@mock.patch("content.media.tts._espeak_turn", _tone)
class PipelineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        cls.academic = Exam.objects.get(code="IELTS_ACADEMIC")
        cls.pte = Exam.objects.get(code="PTE_ACADEMIC")
        cls.user = get_user_model().objects.create_superuser("root", "r@x.io", "pw")

    def qtype(self, exam, code):
        return QT.objects.get(exam=exam, code=code)

    def job(self, exam, code, **kw):
        job = GenerationJob.objects.create(
            exam=exam, question_type=self.qtype(exam, code), count=1, **kw
        )
        return run_job(job)

    def test_mock_job_writes_validated_draft_with_audio(self):
        job = self.job(self.academic, "L_FORM")
        self.assertEqual(job.status, GenerationJob.Status.REVIEW)
        self.assertTrue(job.is_mock)
        draft = job.drafts.get()
        self.assertEqual(draft.status, DraftQuestion.Status.READY)
        audio = draft.media.get(kind="audio").asset
        self.assertEqual(audio.provider, "espeak-ng")
        self.assertGreater(audio.duration_ms, 0)
        self.assertTrue(job.steps.filter(agent="writer", provider="mock").exists())
        self.assertNotIn("transcript", draft.stem)

    def test_publish_creates_stimulus_question_in_pool(self):
        job = self.job(self.pte, "DI", target_pool=GenerationJob.Target.MOCK)
        draft = job.drafts.get()
        question = publish(draft, self.user)
        self.assertEqual(question.origin, Question.Origin.GENERATED)
        self.assertEqual(question.pool, Question.Pool.MOCK)
        self.assertEqual(question.stimulus.image.provider, "matplotlib")
        self.assertEqual(question.content_hash, draft.content_hash)
        with self.assertRaises(PublishError):
            publish(draft, self.user)

    @override_settings(DEBUG=False, CONTENT_ALLOW_MOCK_PUBLISH="")
    def test_mock_drafts_blocked_outside_debug(self):
        draft = self.job(self.pte, "WFD").drafts.get()
        self.assertIn("Mock content can only be published in DEBUG.", blockers(draft))

    def test_exact_duplicate_of_bank_question_is_flagged(self):
        draft = self.job(self.pte, "WFD").drafts.get()
        q = Question.objects.filter(question_type=draft.question_type).first()
        q.content_hash = draft.content_hash
        q.save(update_fields=["content_hash"])
        check_duplicates(draft)
        draft.refresh_from_db()
        self.assertEqual(draft.verdict, "duplicate")
        self.assertTrue(SimilarityHit.objects.filter(draft=draft, method="exact"))
        self.assertIn("Dedup verdict: Duplicate.", blockers(draft))

    def test_copy_guard_flags_source_text(self):
        draft = self.job(self.academic, "R_TFNG").drafts.get()
        SourceDocument.objects.create(
            exam=self.academic, title="Book", pasted_text=draft.stem["passage"]
        )
        from content.pipeline import extract_document

        extract_document(SourceDocument.objects.get(title="Book"))
        check_duplicates(draft)
        draft.refresh_from_db()
        self.assertEqual(draft.verdict, "copy_risk")

    def test_source_upload_extract_and_analyse(self):
        doc = SourceDocument.objects.create(
            exam=self.academic,
            title="Practice book",
            file=SimpleUploadedFile(
                "book.txt",
                b"Questions 1-5. Do the following statements agree? "
                b"Write TRUE, FALSE or NOT GIVEN.\nComplete the summary below.",
            ),
        )
        profiles = analyse_document(doc)
        self.assertEqual(doc.pages.count(), 1)
        self.assertEqual({p.question_type.code for p in profiles}, {"R_TFNG", "R_SUMM"})
        twin = SourceDocument.objects.create(
            exam=self.academic,
            title="Same",
            file=SimpleUploadedFile("again.txt", doc.pages.first().text.encode()[:-1]),
        )
        self.assertIsNotNone(twin.pk)


class ContractTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        cls.exam = Exam.objects.get(code="IELTS_ACADEMIC")

    def test_items_validation_catches_key_errors(self):
        qtype = QT.objects.get(exam=self.exam, code="R_TFNG")
        c = C.ItemsContract(
            title="t",
            topic="x",
            stimulus=C.StimulusSpec(passage="word " * 600 + "The sky is blue."),
            items=[C.Item(n=1, text="s", options=C.TFNG)],
            answers=[C.Answer(key="1", accepted=["TRUE"], evidence="sky is green")],
        )
        codes = {i["code"] for i in C.check(c, qtype)}
        self.assertIn("evidence", codes)
        self.assertIn("items", codes)

    def test_hiw_builds_indices(self):
        qtype = QT.objects.get(exam__code="PTE_ACADEMIC", code="HIW")
        c = C.HiwContract(title="t", topic="x", spoken="a b c d", shown="a x c y")
        self.assertEqual(C.build(c, qtype).answer_key, {"incorrect_indices": [1, 3]})

    def test_minhash_similarity(self):
        a = " ".join(f"word{i}" for i in range(60))
        self.assertGreater(
            dedup.jaccard(dedup.minhash(a), dedup.minhash(a + " x")), 0.9
        )
        self.assertLess(dedup.jaccard(dedup.minhash(a), dedup.minhash("zz " * 60)), 0.1)


class PoolAndExposureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        cls.user = get_user_model().objects.create_user("s", "s@x.io", "pw")

    def test_mock_question_only_in_one_pack(self):
        item = MockPackItem.objects.first()
        other = MockPack.objects.exclude(pk=item.pack_id).first()
        with self.assertRaises(IntegrityError):
            MockPackItem.objects.create(
                pack=other, question=item.question, order=999, section_code="reading"
            )

    def test_practice_lists_exclude_mock_pool_and_prefer_unseen(self):
        qtype = QT.objects.get(exam__code="PTE_ACADEMIC", code="WFD")
        qs = list(questions_for(qtype, Question.objects.all()))
        qs[0].pool = Question.Pool.MOCK
        qs[0].save(update_fields=["pool"])
        visible = list(questions_for(qtype, Question.objects.all()))
        self.assertNotIn(qs[0], visible)
        from django.utils import timezone

        record_exposure(self.user, [visible[0]], PracticeMode.QUESTION, timezone.now())
        record_exposure(self.user, [visible[0]], PracticeMode.QUESTION, timezone.now())
        ordered = list(
            unseen_first(
                Question.objects.filter(pk__in=[v.pk for v in visible]), self.user
            )
        )
        self.assertEqual(ordered[-1], visible[0])
        self.assertEqual(QuestionExposure.objects.get(user=self.user).times_seen, 2)
