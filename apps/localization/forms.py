from django import forms

from .services.parser import MAX_FILE_SIZE


class LocalizationUploadForm(forms.Form):
    file = forms.FileField(help_text="CSV or JSON, UTF-8, up to 5 MB.")
    key_column = forms.CharField(max_length=100, initial="key")
    english_column = forms.CharField(max_length=100, initial="english")
    kazakh_column = forms.CharField(max_length=100, initial="kazakh")
    uzbek_column = forms.CharField(max_length=100, initial="uzbek")
    context_column = forms.CharField(max_length=100, required=False)
    max_length_column = forms.CharField(max_length=100, required=False)

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if uploaded.size > MAX_FILE_SIZE:
            raise forms.ValidationError("File exceeds the 5 MB upload limit.")
        suffix = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
        if suffix not in {"csv", "json"}:
            raise forms.ValidationError("Only CSV and JSON files are supported.")
        return uploaded
