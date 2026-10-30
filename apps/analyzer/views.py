from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.projects.views import accessible_projects

from .models import AnalysisResult
from .providers.base import ProviderError
from .providers.factory import configured_provider
from .services.localization_analyzer import AnalysisError, analyze_entry


@login_required
def analysis_run(request, entry_id: int):
    from apps.localization.models import LocalizationEntry

    entry = get_object_or_404(
        LocalizationEntry.objects.filter(localization_file__project__in=accessible_projects(request.user)), pk=entry_id
    )
    project = entry.localization_file.project
    is_owner = project.owner_id == request.user.id
    can_run = is_owner or project.memberships.filter(user=request.user, role="developer").exists()
    if not can_run:
        messages.error(request, "Reviewers can view analysis, but only project developers can run it.")
        return redirect("project_entries", project_id=project.pk)
    if request.method == "POST":
        language = request.POST.get("language", "kk")
        if language not in {"kk", "uz"}:
            messages.error(request, "Choose Kazakh or Uzbek before running analysis.")
            return redirect("project_entries", project_id=project.pk)
        try:
            provider = configured_provider()
            result = analyze_entry(entry, language, provider, {
                "game_genre": project.game_genre,
                "game_context": project.game_context,
                "terminology": list(project.terminology.values("source_term", "kazakh_translation", "uzbek_translation")),
            })
        except (ProviderError, AnalysisError) as exc:
            messages.error(request, str(exc))
            return redirect("project_entries", project_id=project.pk)
        if result.status == AnalysisResult.Status.NO_ISSUE:
            messages.success(request, "Analysis finished: no issue was flagged. This is an AI assessment, not native-speaker verification.")
            return redirect("project_entries", project_id=project.pk)
        return redirect("analysis_detail", pk=result.pk)
    return redirect("project_entries", project_id=project.pk)


@login_required
def analysis_detail(request, pk: int):
    from apps.reviews.forms import ReviewForm
    from apps.reviews.models import Review

    result = get_object_or_404(
        AnalysisResult.objects.select_related("localization_entry", "localization_entry__localization_file", "localization_entry__localization_file__project"),
        pk=pk,
        localization_entry__localization_file__project__in=accessible_projects(request.user),
    )
    project = result.localization_entry.localization_file.project
    can_review = request.user.is_superuser or project.owner_id == request.user.id or project.memberships.filter(user=request.user, role="reviewer").exists()
    return render(request, "analyzer/detail.html", {
        "result": result, "project": project, "can_review": can_review,
        "review_form": ReviewForm(initial={"final_translation": result.suggested_translation}),
        "reviews": result.reviews.select_related("reviewer"),
        "review_statuses": Review.Status,
    })

# Create your views here.
