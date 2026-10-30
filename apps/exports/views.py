import re
from pathlib import PurePosixPath

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.localization.models import LocalizationFile
from apps.projects.views import accessible_projects

from .forms import ExportForm
from .services import ExportError, build_export


@login_required
def export_file(request, file_id: int):
    localization_file = get_object_or_404(
        LocalizationFile.objects.select_related("project"),
        pk=file_id,
        project__in=accessible_projects(request.user),
    )
    form = ExportForm(request.POST or None, localization_file=localization_file)
    if request.method == "POST" and form.is_valid():
        try:
            content, content_type = build_export(
                localization_file, form.cleaned_data["file_format"], form.cleaned_data["approved_only"]
            )
        except ExportError as exc:
            messages.error(request, str(exc))
        else:
            stem = PurePosixPath(localization_file.original_filename.replace("\\", "/")).stem
            safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "localization"
            suffix = "-approved" if form.cleaned_data["approved_only"] else ""
            response = HttpResponse(content, content_type=content_type)
            response["Content-Disposition"] = f'attachment; filename="{safe_stem}{suffix}.{localization_file.file_format}"'
            return response
    return render(request, "exports/export.html", {"localization_file": localization_file, "form": form})

# Create your views here.
