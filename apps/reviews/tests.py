from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.analyzer.models import AnalysisResult
from apps.localization.models import LocalizationEntry, LocalizationFile
from apps.projects.models import Project, ProjectMember

from .models import Review


class HumanReviewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", password="test-pass-123")
        self.reviewer = user_model.objects.create_user(username="reviewer", password="test-pass-123")
        self.outsider = user_model.objects.create_user(username="outsider", password="test-pass-123")
        self.project = Project.objects.create(owner=self.owner, name="Quest")
        self.file = LocalizationFile.objects.create(
            project=self.project, uploaded_by=self.owner, original_filename="quest.json", file_format="json",
            file=SimpleUploadedFile("quest.json", b"{}"), file_hash="c" * 64,
            upload_status=LocalizationFile.Status.PARSED,
        )
        self.entry = LocalizationEntry.objects.create(
            localization_file=self.file, external_key="start", english_text="Start",
            kazakh_text="Бастау", uzbek_text="Boshlash",
        )
        self.result = AnalysisResult.objects.create(
            localization_entry=self.entry, language="kk", error_type="naturalness", severity="suggestion",
            error_description="Could sound more natural.", current_translation="Бастау",
            suggested_translation="Ойынды бастау", confidence=0.74, analysis_provider="test",
        )

    def _submit(self, user, decision, translation="Ойынды бастау"):
        self.client.force_login(user)
        return self.client.post(reverse("submit_review", args=[self.result.pk]), {
            "decision": decision, "final_translation": translation, "reviewer_comment": "Reviewed in game context.",
        })

    def test_project_reviewer_can_approve_and_apply_translation(self):
        ProjectMember.objects.create(project=self.project, user=self.reviewer, role=ProjectMember.Role.REVIEWER)
        response = self._submit(self.reviewer, Review.Status.APPROVED)
        self.assertRedirects(response, reverse("analysis_detail", args=[self.result.pk]))
        self.entry.refresh_from_db()
        self.result.refresh_from_db()
        review = Review.objects.get(analysis_result=self.result)
        self.assertEqual(self.entry.kazakh_text, "Ойынды бастау")
        self.assertEqual(review.review_status, Review.Status.APPROVED)
        self.assertEqual(self.result.status, AnalysisResult.Status.REVIEWED)

    def test_rejection_records_decision_without_changing_translation(self):
        response = self._submit(self.owner, Review.Status.REJECTED, translation="changed input is ignored")
        self.assertRedirects(response, reverse("analysis_detail", args=[self.result.pk]))
        self.entry.refresh_from_db()
        review = Review.objects.get(analysis_result=self.result)
        self.assertEqual(self.entry.kazakh_text, "Бастау")
        self.assertEqual(review.final_translation, "Бастау")
        self.assertEqual(review.review_status, Review.Status.REJECTED)

    def test_manual_edit_is_saved_as_edit_and_approved(self):
        self._submit(self.owner, Review.Status.EDITED, translation="Ойынды бастау қазір")
        self.entry.refresh_from_db()
        review = Review.objects.get(analysis_result=self.result)
        self.assertEqual(self.entry.kazakh_text, "Ойынды бастау қазір")
        self.assertEqual(review.review_status, Review.Status.EDITED)

    def test_developer_member_and_outsider_cannot_approve(self):
        ProjectMember.objects.create(project=self.project, user=self.reviewer, role=ProjectMember.Role.DEVELOPER)
        response = self._submit(self.reviewer, Review.Status.APPROVED)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Review.objects.exists())
        response = self._submit(self.outsider, Review.Status.APPROVED)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Review.objects.exists())

    def test_review_queue_contains_only_pending_results_in_authorized_projects(self):
        ProjectMember.objects.create(project=self.project, user=self.reviewer, role=ProjectMember.Role.REVIEWER)
        self.client.force_login(self.reviewer)
        response = self.client.get(reverse("review_queue"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "start")
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("review_queue"))
        self.assertNotContains(response, "start")

# Create your tests here.
