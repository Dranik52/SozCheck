"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from apps.accounts.views import SignUpView
from apps.analyzer.views import analysis_detail, analysis_run
from apps.localization.views import entry_list, game_context_preview, upload_localization_file
from apps.projects.views import dashboard, home, project_create, project_delete, project_detail, project_member_remove, project_members, project_update
from apps.reviews.views import review_queue, submit_review
from apps.exports.views import export_file

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    path('projects/new/', project_create, name='project_create'),
    path('projects/<int:pk>/', project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', project_update, name='project_update'),
    path('projects/<int:pk>/delete/', project_delete, name='project_delete'),
    path('projects/<int:pk>/members/', project_members, name='project_members'),
    path('projects/<int:pk>/members/<int:member_id>/remove/', project_member_remove, name='project_member_remove'),
    path('projects/<int:project_id>/localization/upload/', upload_localization_file, name='localization_upload'),
    path('projects/<int:project_id>/strings/', entry_list, name='project_entries'),
    path('strings/<int:entry_id>/preview/', game_context_preview, name='game_context_preview'),
    path('strings/<int:entry_id>/analyze/', analysis_run, name='analysis_run'),
    path('analysis/<int:pk>/', analysis_detail, name='analysis_detail'),
    path('analysis/<int:analysis_id>/review/', submit_review, name='submit_review'),
    path('reviews/', review_queue, name='review_queue'),
    path('localization-files/<int:file_id>/export/', export_file, name='export_file'),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/signup/', SignUpView.as_view(), name='signup'),
]
