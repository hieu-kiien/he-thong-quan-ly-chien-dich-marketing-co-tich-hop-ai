from django.urls import path

from . import views


app_name = "campaigns"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("campaigns/", views.campaign_list, name="list"),
    path("campaigns/new/", views.campaign_create, name="create"),
    path("campaigns/<int:pk>/", views.campaign_detail, name="detail"),
    path("campaigns/<int:pk>/edit/", views.campaign_update, name="update"),
    path("campaigns/<int:campaign_id>/content/new/", views.content_create, name="content-create"),
    path("ai/ideas/", views.ai_ideas, name="ai-ideas"),
]
