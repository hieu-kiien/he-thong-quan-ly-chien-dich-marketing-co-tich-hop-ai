from django.urls import path

from . import views


app_name = "campaigns"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("campaigns/", views.campaign_list, name="list"),
    path("campaigns/new/", views.campaign_create, name="create"),
    path("campaigns/<int:pk>/", views.campaign_detail, name="detail"),
    path("campaigns/<int:pk>/edit/", views.campaign_update, name="update"),
    path("campaigns/<int:pk>/delete/", views.campaign_delete, name="delete"),
    path("campaigns/<int:campaign_id>/content/new/", views.content_create, name="content-create"),
    path("contents/<int:pk>/edit/", views.content_update, name="content-update"),
    path("contents/<int:pk>/delete/", views.content_delete, name="content-delete"),
    path("campaigns/<int:campaign_id>/metrics/new/", views.metric_create, name="metric-create"),
    path("metrics/<int:pk>/edit/", views.metric_update, name="metric-update"),
    path("metrics/<int:pk>/delete/", views.metric_delete, name="metric-delete"),
    path("channels/", views.channel_list, name="channel-list"),
    path("channels/new/", views.channel_create, name="channel-create"),
    path("channels/<int:pk>/edit/", views.channel_update, name="channel-update"),
    path("channels/<int:pk>/delete/", views.channel_delete, name="channel-delete"),
    path("contents/<int:pk>/approve/", views.content_approve, name="content-approve"),
    path("contents/<int:pk>/reject/", views.content_reject, name="content-reject"),
    path("contents/<int:pk>/publish/", views.content_publish, name="content-publish"),
    path("ai/ideas/", views.ai_ideas, name="ai-ideas"),
]
