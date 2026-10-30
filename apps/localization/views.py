import hashlib
from pathlib import PurePosixPath

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render

from apps.projects.models import Project

from .forms import LocalizationUploadForm
from .models import LocalizationEntry, LocalizationFile
from .services.parser import LocalizationParseError, parse_localization_file


@login_required
def upload_localization_file(request, project_id: int):
    project = get_object_or_404(
        Project.objects.filter(Q(owner=request.user) | Q(memberships__user=request.user)), pk=project_id
    )
    is_owner = project.owner_id == request.user.id
    can_upload = is_owner or project.memberships.filter(user=request.user, role="developer").exists()
    if not can_upload:
        return HttpResponseForbidden("Project review members cannot upload localization files.")

    result_file = None
    parse_report = None
    if request.method == "POST":
        form = LocalizationUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["file"]
            content = uploaded.read()
            mapping = {
                "key": form.cleaned_data["key_column"].strip(),
                "en": form.cleaned_data["english_column"].strip(),
                "kk": form.cleaned_data["kazakh_column"].strip(),
                "uz": form.cleaned_data["uzbek_column"].strip(),
                "context": form.cleaned_data["context_column"].strip(),
                "max_length": form.cleaned_data["max_length_column"].strip(),
            }
            try:
                parsed = parse_localization_file(uploaded.name, content, mapping)
                parse_report = parsed.report
                status = LocalizationFile.Status.PARSED
                structure = parsed.original_structure
                entries = parsed.entries
            except LocalizationParseError as exc:
                parse_report = exc.report
                status = LocalizationFile.Status.INVALID
                structure = None
                entries = []

            filename = PurePosixPath(uploaded.name.replace("\\", "/")).name[:255]
            file_format = filename.rsplit(".", 1)[-1].lower()
            with transaction.atomic():
                result_file = LocalizationFile.objects.create(
                    project=project,
                    uploaded_by=request.user,
                    original_filename=filename,
                    file_format=file_format,
                    file_hash=hashlib.sha256(content).hexdigest(),
                    upload_status=status,
                    column_mapping=mapping if file_format == "csv" else {},
                    parsing_report=parse_report,
                    original_structure=structure,
                    file=uploaded,
                )
                if entries:
                    LocalizationEntry.objects.bulk_create([
                        LocalizationEntry(localization_file=result_file, **entry) for entry in entries
                    ])
            if result_file.upload_status == LocalizationFile.Status.PARSED:
                return redirect("project_detail", pk=project.pk)
    else:
        form = LocalizationUploadForm()
    return render(request, "localization/upload.html", {
        "project": project, "form": form, "result_file": result_file, "parse_report": parse_report,
    })


@login_required
def entry_list(request, project_id: int):
    from apps.analyzer.models import AnalysisResult
    from apps.projects.views import accessible_projects

    project = get_object_or_404(accessible_projects(request.user), pk=project_id)
    language = request.GET.get("language", "kk")
    if language not in {"kk", "uz"}:
        language = "kk"
    current_filter = "kazakh_text" if language == "kk" else "uzbek_text"
    latest = AnalysisResult.objects.filter(localization_entry=OuterRef("pk"), language=language).order_by("-created_at")
    entries = LocalizationEntry.objects.filter(
        localization_file__project=project, localization_file__upload_status=LocalizationFile.Status.PARSED,
    ).annotate(
        latest_status=Subquery(latest.values("status")[:1]),
        latest_error_type=Subquery(latest.values("error_type")[:1]),
        latest_severity=Subquery(latest.values("severity")[:1]),
        latest_analysis_id=Subquery(latest.values("id")[:1]),
    )
    query = request.GET.get("q", "").strip()
    if query:
        entries = entries.filter(Q(external_key__icontains=query) | Q(english_text__icontains=query) | Q(**{f"{current_filter}__icontains": query}))
    error_type = request.GET.get("error", "")
    if error_type in AnalysisResult.ErrorType.values:
        entries = entries.filter(latest_error_type=error_type)
    severity = request.GET.get("severity", "")
    if severity in AnalysisResult.Severity.values:
        entries = entries.filter(latest_severity=severity)
    status = request.GET.get("status", "")
    if status == "not_analyzed":
        entries = entries.filter(latest_status__isnull=True)
    elif status == "pending":
        entries = entries.filter(latest_status=AnalysisResult.Status.PENDING)
    elif status == "no_issue":
        entries = entries.filter(latest_status=AnalysisResult.Status.NO_ISSUE)
    page = Paginator(entries.order_by("external_key"), 25).get_page(request.GET.get("page"))
    return render(request, "localization/entry_list.html", {
        "project": project, "page": page, "language": language, "query": query,
        "selected_error": error_type, "selected_severity": severity, "selected_status": status,
        "error_types": AnalysisResult.ErrorType.choices, "severities": AnalysisResult.Severity.choices,
    })


@login_required
def game_context_preview(request, entry_id: int):
    from apps.projects.views import accessible_projects

    entry = get_object_or_404(
        LocalizationEntry.objects.select_related("localization_file", "localization_file__project"),
        pk=entry_id,
        localization_file__project__in=accessible_projects(request.user),
    )
    return render(request, "localization/preview.html", {
        "entry": entry,
        "project": entry.localization_file.project,
        "preview_data": {
            "key": entry.external_key,
            "texts": {"en": entry.english_text, "kk": entry.kazakh_text, "uz": entry.uzbek_text},
            "max_length": entry.max_length,
        },
    })

# Create your views here.
