from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("analysis_result", "reviewer", "review_status", "reviewed_at")
    list_filter = ("review_status", "reviewed_at")
    search_fields = ("analysis_result__localization_entry__external_key", "reviewer__username", "reviewer_comment")
    readonly_fields = ("analysis_result", "reviewer", "original_translation", "final_translation", "review_status", "reviewer_comment", "reviewed_at")

# Register your models here.
