from django.conf import settings
from django.db import models


class Project(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_projects")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    game_genre = models.CharField(max_length=100, blank=True)
    game_context = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "name"]
        indexes = [models.Index(fields=["owner", "-updated_at"], name="project_owner_updated_idx")]

    def __str__(self) -> str:
        return self.name


class ProjectMember(models.Model):
    class Role(models.TextChoices):
        DEVELOPER = "developer", "Developer"
        REVIEWER = "reviewer", "Reviewer"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DEVELOPER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "user"], name="unique_project_member")]
        indexes = [models.Index(fields=["user", "role"], name="project_member_user_role_idx")]

    def __str__(self) -> str:
        return f"{self.user} — {self.project} ({self.role})"

# Create your models here.
