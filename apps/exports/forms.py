from django import forms

from apps.localization.models import LocalizationFile


class ExportForm(forms.Form):
    file_format = forms.ChoiceField(choices=(("csv", "CSV"), ("json", "JSON")))
    approved_only = forms.BooleanField(required=False, label="Only apply human-approved corrections")

    def __init__(self, *args, localization_file: LocalizationFile, **kwargs):
        super().__init__(*args, **kwargs)
        label = "CSV" if localization_file.file_format == "csv" else "JSON"
        self.fields["file_format"].choices = ((localization_file.file_format, label),)
        self.fields["file_format"].initial = localization_file.file_format
