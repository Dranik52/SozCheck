from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProjectForm, ProjectMemberForm
from .models import Project, ProjectMember


def accessible_projects(user):
    return Project.objects.filter(Q(owner=user) | Q(memberships__user=user)).distinct()


def home(request):
    if request.user.is_authenticated:
        return dashboard(request)
    return render(request, "home.html")


@login_required
def dashboard(request):
    from apps.analyzer.models import AnalysisResult
    from apps.localization.models import LocalizationEntry

    projects = accessible_projects(request.user)
    entries = LocalizationEntry.objects.filter(localization_file__project__in=projects)
    analyses = AnalysisResult.objects.filter(localization_entry__localization_file__project__in=projects)
    recent_activity = analyses.select_related("localization_entry", "localization_entry__localization_file").order_by("-created_at")[:6]
    stats = {
        "project_count": projects.count(),
        "string_count": entries.count(),
        "analyzed_count": entries.filter(analysis_results__isnull=False).distinct().count(),
        "critical_count": analyses.filter(severity=AnalysisResult.Severity.CRITICAL, status=AnalysisResult.Status.PENDING).count(),
        "pending_count": analyses.filter(status=AnalysisResult.Status.PENDING).count(),
    }
    return render(request, "dashboard.html", {"projects": projects, "stats": stats, "recent_activity": recent_activity})


@login_required
def project_detail(request, pk: int):
    project = get_object_or_404(
        accessible_projects(request.user), pk=pk
    )
    is_owner = project.owner_id == request.user.id
    can_upload = is_owner or project.memberships.filter(user=request.user, role="developer").exists()
    return render(request, "projects/detail.html", {"project": project, "is_owner": is_owner, "can_upload": can_upload})


@login_required
def project_create(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            return redirect("project_detail", pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, "projects/form.html", {"form": form, "heading": "Create a project"})


@login_required
def project_update(request, pk: int):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect("project_detail", pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, "projects/form.html", {"form": form, "heading": "Edit project", "project": project})


@login_required
def project_delete(request, pk: int):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    if request.method == "POST":
        project.delete()
        return redirect("dashboard")
    return render(request, "projects/confirm_delete.html", {"project": project})


@login_required
def project_members(request, pk: int):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    if request.method == "POST":
        form = ProjectMemberForm(request.POST, project=project)
        if form.is_valid():
            membership = form.save(commit=False)
            membership.project = project
            membership.save()
            return redirect("project_members", pk=project.pk)
    else:
        form = ProjectMemberForm(project=project)
    return render(request, "projects/members.html", {"project": project, "form": form})


@login_required
def project_member_remove(request, pk: int, member_id: int):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    membership = get_object_or_404(ProjectMember, pk=member_id, project=project)
    if request.method != "POST":
        return HttpResponseForbidden("Member removal requires a POST request.")
    membership.delete()
    return redirect("project_members", pk=project.pk)

# Create your views here.
