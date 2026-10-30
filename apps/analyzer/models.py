from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class AnalysisResult(models.Model):
    class Language(models.TextChoices):
        KAZAKH = "kk", "Kazakh"
        UZBEK = "uz", "Uzbek"

    class ErrorType(models.TextChoices):
        NONE = "none", "No issue"
        GRAMMAR = "grammar", "Grammar"
        SPELLING = "spelling", "Spelling"
        MEANING = "meaning", "Meaning"
        CONTEXT = "context", "Context"
        TERMINOLOGY = "terminology", "Terminology"
        TONE = "tone", "Tone"
        PLACEHOLDER = "placeholder", "Placeholder"
        LENGTH = "length", "Length"
        NATURALNESS = "naturalness", "Naturalness"

    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        MAJOR = "major", "Major"
        MINOR = "minor", "Minor"
        SUGGESTION = "suggestion", "Suggestion"

    class Status(models.TextChoices):
        PENDING = "pending_review", "Pending human review"
        NO_ISSUE = "no_issue", "No issue found"
        REVIEWED = "reviewed", "Reviewed"

    localization_entry = models.ForeignKey("localization.LocalizationEntry", on_delete=models.CASCADE, related_name="analysis_results")
    language = models.CharField(max_length=2, choices=Language.choices)
    error_type = models.CharField(max_length=20, choices=ErrorType.choices)
    severity = models.CharField(max_length=12, choices=Severity.choices, default=Severity.SUGGESTION)
    error_description = models.TextField(blank=True)
    current_translation = models.TextField()
    suggested_translation = models.TextField(blank=True)
    confidence = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    requires_human_review = models.BooleanField(default=True)
    analysis_provider = models.CharField(max_length=32)
    model_name = models.CharField(max_length=100, blank=True)
    prompt_version = models.CharField(max_length=32, default="v1")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["localization_entry", "language", "-created_at"], name="analysis_entry_lang_date_idx")]

    def __str__(self) -> str:
        return f"{self.get_language_display()} analysis for {self.localization_entry}"


class Terminology(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="terminology")
    source_term = models.CharField(max_length=200)
    kazakh_translation = models.CharField(max_length=200, blank=True)
    uzbek_translation = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_term"]
        constraints = [models.UniqueConstraint(fields=["project", "source_term"], name="unique_project_term")]

    def __str__(self) -> str:
        return f"{self.source_term} ({self.project})"

# Create your models here.
