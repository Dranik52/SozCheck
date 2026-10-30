import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.projects.models import Project, ProjectMember

from .models import LocalizationEntry, LocalizationFile
from .services.parser import LocalizationParseError, parse_localization_file


class LocalizationParserTests(TestCase):
    def test_valid_csv_with_unicode_translations(self):
        data = "key,english,kazakh,uzbek\nstart,Start,Бастау,Boshlash\n".encode()
        result = parse_localization_file("strings.csv", data)
        self.assertEqual(result.entries[0]["kazakh_text"], "Бастау")
        self.assertEqual(result.entries[0]["uzbek_text"], "Boshlash")

    def test_csv_column_mapping_and_uzbek_cyrillic(self):
        data = "id,src,kk,uz-Cyrl\nstart,Start,Бастау,Бошлаш\n".encode()
        result = parse_localization_file("strings.csv", data, {
            "key": "id", "en": "src", "kk": "kk", "uz": "uz-Cyrl",
        })
        self.assertEqual(result.entries[0]["uzbek_text"], "Бошлаш")

    def test_csv_context_length_and_extra_metadata_are_imported(self):
        data = "id,src,kk,uz,context,limit,tag\nstart,Start,Бастау,Boshlash,Main menu,24,button\n".encode()
        result = parse_localization_file("strings.csv", data, {
            "key": "id", "en": "src", "kk": "kk", "uz": "uz", "context": "context", "max_length": "limit",
        })
        self.assertEqual(result.entries[0]["context"], "Main menu")
        self.assertEqual(result.entries[0]["max_length"], 24)
        self.assertEqual(result.entries[0]["metadata"], {"tag": "button"})

    def test_csv_reports_missing_columns_duplicate_keys_and_empty_values(self):
        with self.assertRaises(LocalizationParseError) as missing:
            parse_localization_file("strings.csv", b"key,en\na,b\n")
        self.assertIn("Mapped column", missing.exception.report["errors"][0])
        with self.assertRaises(LocalizationParseError) as invalid:
            parse_localization_file("strings.csv", "key,english,kazakh,uzbek\nx,A,B,C\nx,D,,E\n".encode())
        report = " ".join(invalid.exception.report["errors"])
        self.assertIn("duplicate key", report)

    def test_invalid_json_is_reported(self):
        with self.assertRaises(LocalizationParseError) as error:
            parse_localization_file("strings.json", b"{not-json")
        self.assertIn("Invalid JSON", error.exception.report["errors"][0])

    def test_nested_json_paths_and_original_structure_are_preserved(self):
        structure = {"ui": {"start": {"en": "Start", "kk": "Бастау", "uz": "Boshlash", "context": "Main menu", "max_length": 24, "voice": "friendly"}}}
        result = parse_localization_file("strings.json", json.dumps(structure, ensure_ascii=False).encode())
        self.assertEqual(result.entries[0]["source_path"], ["ui", "start"])
        self.assertEqual(result.entries[0]["context"], "Main menu")
        self.assertEqual(result.entries[0]["max_length"], 24)
        self.assertEqual(result.entries[0]["metadata"], {"voice": "friendly"})
        self.assertEqual(result.original_structure, structure)

    def test_csv_parser_keeps_original_headers_and_unmapped_columns(self):
        data = "id,src,kk,uz,notes\nstart,Start,Бастау,Boshlash,UI button\n".encode()
        result = parse_localization_file("strings.csv", data, {"key": "id", "en": "src", "kk": "kk", "uz": "uz"})
        self.assertEqual(result.original_structure["headers"], ["id", "src", "kk", "uz", "notes"])
        self.assertEqual(result.original_structure["rows"][0]["notes"], "UI button")

    def test_json_detects_missing_language_empty_values_and_duplicate_object_keys(self):
        with self.assertRaises(LocalizationParseError) as missing:
            parse_localization_file("strings.json", b'{"a":{"en":"Hi","kk":"","uz":"Salom"}}')
        self.assertIn("missing or empty", missing.exception.report["errors"][0])
        with self.assertRaises(LocalizationParseError) as duplicate:
            parse_localization_file("strings.json", b'{"a":{"en":"one","en":"two","kk":"","uz":""}}')
        self.assertIn("Duplicate JSON key", duplicate.exception.report["errors"][0])

    def test_rejects_wrong_extension_oversize_and_non_utf8(self):
        for name, content in (("x.exe", b"x"), ("x.csv", b"\xff"), ("x.csv", b"x" * (5 * 1024 * 1024 + 1))):
            with self.subTest(name=name), self.assertRaises(LocalizationParseError):
                parse_localization_file(name, content)


class LocalizationUploadPermissionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", password="test-pass-123")
        self.reviewer = user_model.objects.create_user(username="reviewer", password="test-pass-123")
        self.project = Project.objects.create(owner=self.owner, name="Language Quest")

    def _upload(self, username, role=None):
        if role:
            ProjectMember.objects.create(project=self.project, user=self.reviewer, role=role)
            user = self.reviewer
        else:
            user = self.owner if username == "owner" else self.reviewer
        self.client.force_login(user)
        file = SimpleUploadedFile("texts.csv", "key,english,kazakh,uzbek\nopen,Open,Ашу,Ochish\n".encode(), content_type="text/csv")
        return self.client.post(f"/projects/{self.project.pk}/localization/upload/", {
            "file": file, "key_column": "key", "english_column": "english",
            "kazakh_column": "kazakh", "uzbek_column": "uzbek",
        })

    def test_owner_uploads_and_entries_are_saved(self):
        response = self._upload("owner")
        self.assertEqual(response.status_code, 302)
        uploaded = LocalizationFile.objects.get(project=self.project)
        self.assertEqual(uploaded.upload_status, LocalizationFile.Status.PARSED)
        self.assertEqual(LocalizationEntry.objects.filter(localization_file=uploaded).count(), 1)

    def test_reviewer_cannot_upload(self):
        response = self._upload("reviewer", role=ProjectMember.Role.REVIEWER)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LocalizationFile.objects.exists())

    def test_deleting_project_removes_its_private_original_upload(self):
        uploaded = LocalizationFile.objects.create(
            project=self.project, uploaded_by=self.owner, original_filename="private.csv", file_format="csv",
            file=SimpleUploadedFile("private.csv", b"original data"), file_hash="f" * 64,
            upload_status=LocalizationFile.Status.INVALID,
        )
        path = uploaded.file.path
        self.assertTrue(Path(path).exists())
        self.project.delete()
        self.assertFalse(Path(path).exists())

    def test_preview_shows_real_project_translation_and_is_project_scoped(self):
        uploaded = LocalizationFile.objects.create(
            project=self.project, uploaded_by=self.owner, original_filename="preview.csv", file_format="csv",
            file=SimpleUploadedFile("preview.csv", b"key,english,kazakh,uzbek\nopen,Open,Hello,Salom\n"),
            file_hash="d" * 64, upload_status=LocalizationFile.Status.PARSED,
        )
        entry = LocalizationEntry.objects.create(
            localization_file=uploaded, external_key="open", english_text="Open",
            kazakh_text="Ашу", uzbek_text="Ochish", max_length=12,
        )
        self.client.force_login(self.owner)
        response = self.client.get(f"/strings/{entry.pk}/preview/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SIMULATED GAME UI")
        self.assertContains(response, r"\u0410\u0448\u0443")
        self.assertContains(response, "12")
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(f"/strings/{entry.pk}/preview/").status_code, 404)

# Create your tests here.
