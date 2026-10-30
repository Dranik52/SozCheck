import uuid

from django.conf import settings
from django.db import models


def original_upload_path(instance: "LocalizationFile", filename: str) -> str:
    """Store each source under an opaque name, never a user-controlled path."""
    extension = instance.file_format if instance.file_format in {"csv", "json"} else "bin"
    return f"localization/{instance.project_id}/{uuid.uuid4().hex}.{extension}"


class LocalizationFile(models.Model):
    class Format(models.TextChoices):
        CSV = "csv", "CSV"
        JSON = "json", "JSON"

    class Status(models.TextChoices):
        PARSED = "parsed", "Parsed"
        INVALID = "invalid", "Invalid"

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="localization_files")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="localization_uploads")
    original_filename = models.CharField(max_length=255)
    file_format = models.CharField(max_length=8, choices=Format.choices)
    file = models.FileField(upload_to=original_upload_path)
    file_hash = models.CharField(max_length=64)
    upload_status = models.CharField(max_length=16, choices=Status.choices)
    column_mapping = models.JSONField(default=dict, blank=True)
    parsing_report = models.JSONField(default=dict, blank=True)
    original_structure = models.JSONField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [models.Index(fields=["project", "upload_status"], name="locfile_project_status_idx")]

    def __str__(self) -> str:
        return self.original_filename


class LocalizationEntry(models.Model):
    localization_file = models.ForeignKey(LocalizationFile, on_delete=models.CASCADE, related_name="entries")
    external_key = models.CharField(max_length=512)
    english_text = models.TextField()
    kazakh_text = models.TextField(blank=True)
    uzbek_text = models.TextField(blank=True)
    context = models.TextField(blank=True)
    max_length = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    source_path = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["external_key"]
        constraints = [models.UniqueConstraint(fields=["localization_file", "external_key"], name="unique_file_entry_key")]
        indexes = [models.Index(fields=["localization_file", "external_key"], name="entry_file_key_idx")]

    def __str__(self) -> str:
        return self.external_key

# Create your models here.
