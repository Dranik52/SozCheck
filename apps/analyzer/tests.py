import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.localization.models import LocalizationEntry, LocalizationFile
from apps.projects.models import Project

from .models import AnalysisResult
from .providers.base import ProviderError
from .services.localization_analyzer import AnalysisError, analyze_entry
from .services.placeholder_checker import extract_placeholders, placeholders_match
from .services.response_validator import InvalidAnalysisResponse, validate_analysis_response


VALID_ISSUE = {
    "has_issue": True,
    "error_type": "naturalness",
    "severity": "suggestion",
    "error_description": "The phrase may sound unnatural in this game context.",
    "suggested_translation": "Бастау",
    "confidence": 0.72,
}


class StubProvider:
    name = "test"
    model = "stub-model"

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        if self.error:
            raise self.error
        return json.dumps(self.result, ensure_ascii=False)


class AnalyzerServiceTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="analyst", password="test-pass-123")
        project = Project.objects.create(owner=user, name="Skyline")
        localization_file = LocalizationFile.objects.create(
            project=project, uploaded_by=user, original_filename="sample.json", file_format="json",
            file=SimpleUploadedFile("sample.json", b"{}"), file_hash="a" * 64,
            upload_status=LocalizationFile.Status.PARSED,
        )
        self.entry = LocalizationEntry.objects.create(
            localization_file=localization_file, external_key="start", english_text="Start",
            kazakh_text="Бастау", uzbek_text="Boshlash",
        )

    def test_valid_structured_issue_is_accepted(self):
        result = validate_analysis_response(VALID_ISSUE, "Бастау", "Start")
        self.assertEqual(result["error_type"], "naturalness")
        self.assertEqual(result["confidence"], 0.72)

    def test_invalid_json_missing_fields_and_confidence_are_rejected(self):
        with self.assertRaises(InvalidAnalysisResponse):
            validate_analysis_response("not json", "Бастау", "Start")
        with self.assertRaises(InvalidAnalysisResponse):
            validate_analysis_response({"has_issue": True}, "Бастау", "Start")
        invalid_confidence = {**VALID_ISSUE, "confidence": 2}
        with self.assertRaises(InvalidAnalysisResponse):
            validate_analysis_response(invalid_confidence, "Бастау", "Start")

    def test_no_issue_response_must_preserve_translation(self):
        no_issue = {"has_issue": False, "error_type": "none", "severity": "suggestion",
                    "error_description": "", "suggested_translation": "Different", "confidence": 0.9}
        with self.assertRaises(InvalidAnalysisResponse):
            validate_analysis_response(no_issue, "Бастау", "Start")

    def test_placeholder_comparison_preserves_repeated_tokens(self):
        self.assertEqual(extract_placeholders("{player} %s %s"), {"{player}": 1, "%s": 2})
        self.assertTrue(placeholders_match("Open {player} (%d)", "Ашу {player} (%d)"))
        self.assertFalse(placeholders_match("Open {player} %d", "Ашу {name} %d"))

    def test_placeholder_issue_is_reported_without_claiming_a_fix(self):
        self.entry.english_text = "Welcome, {player}!"
        self.entry.kazakh_text = "Қош келдіңіз!"
        self.entry.save()
        result = analyze_entry(self.entry, "kk", StubProvider())
        self.assertEqual(result.error_type, AnalysisResult.ErrorType.PLACEHOLDER)
        self.assertEqual(result.suggested_translation, self.entry.kazakh_text)
        self.assertTrue(result.requires_human_review)
        self.assertEqual(result.analysis_provider, "local")

    def test_provider_issue_is_saved_pending_human_review(self):
        provider = StubProvider(VALID_ISSUE)
        result = analyze_entry(self.entry, "kk", provider, {"game_genre": "Adventure"})
        self.assertEqual(provider.calls, 1)
        self.assertEqual(result.status, AnalysisResult.Status.PENDING)
        self.assertTrue(result.requires_human_review)
        self.assertEqual(result.analysis_provider, "test")

    def test_provider_timeout_is_reported_and_not_saved_as_result(self):
        provider = StubProvider(error=ProviderError("timeout"))
        with self.assertRaises(AnalysisError):
            analyze_entry(self.entry, "kk", provider)
        self.assertFalse(AnalysisResult.objects.exists())


class AnalysisWorkflowViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", password="test-pass-123")
        self.other = user_model.objects.create_user(username="other", password="test-pass-123")
        self.project = Project.objects.create(owner=self.owner, name="Quest")
        localization_file = LocalizationFile.objects.create(
            project=self.project, uploaded_by=self.owner, original_filename="game.csv", file_format="csv",
            file=SimpleUploadedFile("game.csv", b"key,english,kazakh,uzbek\na,b,c,d\n"),
            file_hash="b" * 64, upload_status=LocalizationFile.Status.PARSED,
        )
        self.entry = LocalizationEntry.objects.create(
            localization_file=localization_file, external_key="welcome", english_text="Hi {player}",
            kazakh_text="Сәлем", uzbek_text="Salom",
        )

    def test_project_string_table_shows_only_accessible_project(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("project_entries", args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "welcome")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("project_entries", args=[self.project.pk])).status_code, 404)

    def test_local_placeholder_check_is_available_without_provider_key(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("analysis_run", args=[self.entry.pk]), {"language": "kk"})
        result = AnalysisResult.objects.get(localization_entry=self.entry)
        self.assertRedirects(response, reverse("analysis_detail", args=[result.pk]))
        self.assertEqual(result.error_type, AnalysisResult.ErrorType.PLACEHOLDER)

    def test_analysis_details_are_project_scoped(self):
        result = AnalysisResult.objects.create(
            localization_entry=self.entry, language="kk", error_type="placeholder", severity="major",
            error_description="Missing token", current_translation="Сәлем", suggested_translation="Сәлем",
            confidence=1, analysis_provider="local",
        )
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("analysis_detail", args=[result.pk])).status_code, 404)
