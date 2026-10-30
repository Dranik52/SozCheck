from django.contrib import admin

from .models import LocalizationEntry, LocalizationFile


class LocalizationEntryInline(admin.TabularInline):
    model = LocalizationEntry
    extra = 0
    readonly_fields = ("external_key", "english_text", "kazakh_text", "uzbek_text", "source_path")
    can_delete = False


@admin.register(LocalizationFile)
class LocalizationFileAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "project", "file_format", "upload_status", "uploaded_at")
    list_filter = ("file_format", "upload_status")
    search_fields = ("original_filename", "project__name")
    readonly_fields = ("file", "file_hash", "uploaded_by", "uploaded_at", "parsing_report", "original_structure")
    inlines = (LocalizationEntryInline,)


@admin.register(LocalizationEntry)
class LocalizationEntryAdmin(admin.ModelAdmin):
    list_display = ("external_key", "localization_file", "updated_at")
    search_fields = ("external_key", "english_text", "kazakh_text", "uzbek_text")
    list_select_related = ("localization_file",)
    readonly_fields = tuple(field.name for field in LocalizationEntry._meta.fields)
