from django.conf import settings
from django.db import models


class Review(models.Model):
    class Status(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EDITED = "edited", "Edited and approved"

    analysis_result = models.ForeignKey("analyzer.AnalysisResult", on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="localization_reviews")
    original_translation = models.TextField()
    final_translation = models.TextField()
    review_status = models.CharField(max_length=12, choices=Status.choices)
    reviewer_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reviewed_at"]
        indexes = [models.Index(fields=["analysis_result", "-reviewed_at"], name="review_result_date_idx")]

    def __str__(self) -> str:
        return f"{self.get_review_status_display()} by {self.reviewer}"

# Create your models here.
