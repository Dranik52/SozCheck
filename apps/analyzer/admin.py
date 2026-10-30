from django.contrib import admin

from .models import AnalysisResult, Terminology


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ("localization_entry", "language", "error_type", "severity", "status", "created_at")
    list_filter = ("language", "error_type", "severity", "status", "analysis_provider")
    search_fields = ("localization_entry__external_key", "error_description")
    readonly_fields = tuple(field.name for field in AnalysisResult._meta.fields)


@admin.register(Terminology)
class TerminologyAdmin(admin.ModelAdmin):
    list_display = ("source_term", "project", "kazakh_translation", "uzbek_translation", "category")
    search_fields = ("source_term", "project__name")
    list_filter = ("category",)
