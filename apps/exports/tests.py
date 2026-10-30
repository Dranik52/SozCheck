import csv
import io
import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.analyzer.models import AnalysisResult
from apps.localization.models import LocalizationEntry, LocalizationFile
from apps.projects.models import Project
from apps.reviews.models import Review

from .services import ExportError, build_export


class ExportServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="exporter", password="test-pass-123")
        self.other = get_user_model().objects.create_user(username="other", password="test-pass-123")
        self.project = Project.objects.create(owner=self.user, name="Runner")

    def make_file(self, name, file_format, structure, mapping=None):
        return LocalizationFile.objects.create(
            project=self.project, uploaded_by=self.user, original_filename=name, file_format=file_format,
            file=SimpleUploadedFile(name, b"original upload"), file_hash="e" * 64,
            upload_status=LocalizationFile.Status.PARSED, column_mapping=mapping or {}, original_structure=structure,
        )

    def test_csv_export_preserves_unmapped_columns_and_uses_current_text(self):
        file = self.make_file("game.csv", "csv", {
            "headers": ["id", "source", "kk", "uz", "note"],
            "rows": [{"id": "open", "source": "Open", "kk": "Ашу", "uz": "Ochish", "note": "button"}],
        }, {"key": "id", "en": "source", "kk": "kk", "uz": "uz"})
        entry = LocalizationEntry.objects.create(
            localization_file=file, external_key="open", english_text="Open", kazakh_text="Ашу сейчас",
            uzbek_text="Ochish", source_path=["open"],
        )
        content, content_type = build_export(file, "csv")
        row = next(csv.DictReader(io.StringIO(content)))
        self.assertEqual(content_type, "text/csv; charset=utf-8")
        self.assertEqual(row["kk"], "Ашу сейчас")
        self.assertEqual(row["note"], "button")

    def test_json_approved_only_applies_approved_edits_and_preserves_structure(self):
        structure = {"ui": {"start": {"en": "Start {player}", "kk": "Бастау {player}", "uz": "Boshlash {player}"}}, "version": 2}
        file = self.make_file("nested.json", "json", structure)
        entry = LocalizationEntry.objects.create(
            localization_file=file, external_key="ui.start", english_text="Start {player}",
            kazakh_text="Бастау {player}", uzbek_text="Boshlash {player}", source_path=["ui", "start"],
        )
        analysis = AnalysisResult.objects.create(
            localization_entry=entry, language="kk", error_type="naturalness", severity="suggestion",
            error_description="Style", current_translation="Бастау {player}",
            suggested_translation="Ойынды баста {player}", confidence=0.8, analysis_provider="test",
        )
        Review.objects.create(
            analysis_result=analysis, reviewer=self.user, original_translation="Бастау {player}",
            final_translation="Ойынды баста {player}", review_status=Review.Status.EDITED,
        )
        content, _ = build_export(file, "json", approved_only=True)
        exported = json.loads(content)
        self.assertEqual(exported["ui"]["start"]["kk"], "Ойынды баста {player}")
        self.assertEqual(exported["ui"]["start"]["uz"], "Boshlash {player}")
        self.assertEqual(exported["version"], 2)
        self.assertEqual(structure["ui"]["start"]["kk"], "Бастау {player}")

    def test_rejected_suggestion_is_not_exported(self):
        structure = {"start": {"en": "Start", "kk": "Бастау", "uz": "Boshlash"}}
        file = self.make_file("game.json", "json", structure)
        entry = LocalizationEntry.objects.create(
            localization_file=file, external_key="start", english_text="Start", kazakh_text="Бастау",
            uzbek_text="Boshlash", source_path=["start"],
        )
        analysis = AnalysisResult.objects.create(
            localization_entry=entry, language="kk", error_type="naturalness", severity="suggestion",
            error_description="Style", current_translation="Бастау", suggested_translation="Бастаңыз",
            confidence=0.8, analysis_provider="test",
        )
        Review.objects.create(
            analysis_result=analysis, reviewer=self.user, original_translation="Бастау",
            final_translation="Бастау", review_status=Review.Status.REJECTED,
        )
        content, _ = build_export(file, "json", approved_only=True)
        self.assertEqual(json.loads(content)["start"]["kk"], "Бастау")

    def test_placeholder_mismatch_blocks_export(self):
        structure = {"start": {"en": "Get {coins}", "kk": "Алу {coins}", "uz": "Olish {coins}"}}
        file = self.make_file("game.json", "json", structure)
        LocalizationEntry.objects.create(
            localization_file=file, external_key="start", english_text="Get {coins}",
            kazakh_text="Алу", uzbek_text="Olish {coins}", source_path=["start"],
        )
        with self.assertRaises(ExportError):
            build_export(file, "json")

    def test_export_download_is_project_scoped_and_keeps_original_filename_safe(self):
        file = self.make_file("../game.json", "json", {"start": {"en": "Start", "kk": "Бастау", "uz": "Boshlash"}})
        LocalizationEntry.objects.create(
            localization_file=file, external_key="start", english_text="Start", kazakh_text="Бастау",
            uzbek_text="Boshlash", source_path=["start"],
        )
        self.client.force_login(self.user)
        response = self.client.post(reverse("export_file", args=[file.pk]), {"file_format": "json"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="game.json"')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("export_file", args=[file.pk])).status_code, 404)
