from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.analyzer.models import AnalysisResult
from apps.projects.models import Project

from .forms import ReviewForm
from .models import Review


@login_required
def review_queue(request):
    projects = Project.objects.filter(Q(owner=request.user) | Q(memberships__user=request.user, memberships__role="reviewer"))
    results = AnalysisResult.objects.filter(
        status=AnalysisResult.Status.PENDING,
        localization_entry__localization_file__project__in=projects,
    ).select_related("localization_entry", "localization_entry__localization_file", "localization_entry__localization_file__project")
    return render(request, "reviews/queue.html", {"results": results})


@login_required
def submit_review(request, analysis_id: int):
    result = get_object_or_404(
        AnalysisResult.objects.select_related("localization_entry", "localization_entry__localization_file__project"),
        pk=analysis_id,
    )
    project = result.localization_entry.localization_file.project
    is_reviewer = request.user.is_superuser or project.owner_id == request.user.id or project.memberships.filter(user=request.user, role="reviewer").exists()
    if not is_reviewer:
        return HttpResponseForbidden("You are not authorized to review this project's translations.")
    if result.status != AnalysisResult.Status.PENDING or not result.requires_human_review:
        messages.info(request, "This item is not waiting for human review.")
        return redirect("analysis_detail", pk=result.pk)
    if request.method != "POST":
        return redirect("analysis_detail", pk=result.pk)
    form = ReviewForm(request.POST, instance=Review(
        analysis_result=result, reviewer=request.user,
        original_translation=result.current_translation,
        final_translation=result.suggested_translation,
    ))
    if form.is_valid():
        decision = form.cleaned_data["decision"]
        final_translation = form.cleaned_data["final_translation"]
        if decision == Review.Status.REJECTED:
            final_translation = result.current_translation
        elif decision == Review.Status.APPROVED:
            final_translation = result.suggested_translation
        with transaction.atomic():
            review = form.save(commit=False)
            review.analysis_result = result
            review.reviewer = request.user
            review.original_translation = result.current_translation
            review.final_translation = final_translation
            review.review_status = decision
            review.reviewed_at = timezone.now()
            review.save()
            result.status = AnalysisResult.Status.REVIEWED
            result.save(update_fields=["status"])
            if decision in {Review.Status.APPROVED, Review.Status.EDITED}:
                entry = result.localization_entry
                if result.language == AnalysisResult.Language.KAZAKH:
                    entry.kazakh_text = final_translation
                else:
                    entry.uzbek_text = final_translation
                entry.save(update_fields=["kazakh_text" if result.language == "kk" else "uzbek_text", "updated_at"])
        messages.success(request, f"Review saved as {review.get_review_status_display()}.")
        return redirect("analysis_detail", pk=result.pk)
    messages.error(request, "Please correct the review form and try again.")
    return redirect("analysis_detail", pk=result.pk)

# Create your views here.
