from django import forms
from django.contrib.auth import get_user_model

from .models import Project, ProjectMember


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "description", "game_genre", "game_context")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "game_context": forms.Textarea(attrs={"rows": 5}),
        }


class ProjectMemberForm(forms.ModelForm):
    class Meta:
        model = ProjectMember
        fields = ("user", "role")

    def __init__(self, *args, project: Project, **kwargs):
        super().__init__(*args, **kwargs)
        existing = project.memberships.values_list("user_id", flat=True)
        self.fields["user"].queryset = get_user_model().objects.filter(is_active=True).exclude(
            pk=project.owner_id
        ).exclude(pk__in=existing).order_by("username")
