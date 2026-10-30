from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Project, ProjectMember


User = get_user_model()


class ProjectAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="test-pass-123")
        self.other = User.objects.create_user(username="other", password="test-pass-123")
        self.project = Project.objects.create(owner=self.owner, name="Puzzle Quest")

    def test_owner_can_open_project(self):
        self.client.force_login(self.owner)
        response = self.client.get(f"/projects/{self.project.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_unrelated_user_cannot_open_project(self):
        self.client.force_login(self.other)
        response = self.client.get(f"/projects/{self.project.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_member_can_view_but_cannot_edit_project(self):
        ProjectMember.objects.create(project=self.project, user=self.other, role=ProjectMember.Role.REVIEWER)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f"/projects/{self.project.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/projects/{self.project.pk}/edit/").status_code, 404)

    def test_project_creation_assigns_current_user_as_owner(self):
        self.client.force_login(self.other)
        response = self.client.post("/projects/new/", {
            "name": "Forest Run", "description": "A mobile adventure", "game_genre": "Adventure",
            "game_context": "A small forest world.",
        })
        created = Project.objects.get(name="Forest Run")
        self.assertEqual(created.owner, self.other)
        self.assertRedirects(response, f"/projects/{created.pk}/")


class AuthenticationPageTests(TestCase):
    def test_public_landing_and_signup_are_available(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/accounts/signup/").status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)


class ProjectMemberManagementTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="test-pass-123")
        self.member = User.objects.create_user(username="reviewer", password="test-pass-123")
        self.other = User.objects.create_user(username="other", password="test-pass-123")
        self.project = Project.objects.create(owner=self.owner, name="Co-op Adventure")

    def test_owner_can_add_reviewer_but_other_user_cannot_manage_members(self):
        self.client.force_login(self.owner)
        response = self.client.post(f"/projects/{self.project.pk}/members/", {
            "user": self.member.pk, "role": ProjectMember.Role.REVIEWER,
        })
        self.assertRedirects(response, f"/projects/{self.project.pk}/members/")
        self.assertTrue(self.project.memberships.filter(user=self.member, role=ProjectMember.Role.REVIEWER).exists())
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f"/projects/{self.project.pk}/members/").status_code, 404)

    def test_owner_can_remove_member_only_with_post(self):
        membership = ProjectMember.objects.create(project=self.project, user=self.member, role=ProjectMember.Role.REVIEWER)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(f"/projects/{self.project.pk}/members/{membership.pk}/remove/").status_code, 403)
        response = self.client.post(f"/projects/{self.project.pk}/members/{membership.pk}/remove/")
        self.assertRedirects(response, f"/projects/{self.project.pk}/members/")
        self.assertFalse(ProjectMember.objects.filter(pk=membership.pk).exists())

# Create your tests here.
