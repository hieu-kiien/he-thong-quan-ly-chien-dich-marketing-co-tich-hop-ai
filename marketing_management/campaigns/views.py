from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .ai_service import MarketingAIService
from .forms import CampaignForm, ContentForm
from .models import Campaign
from .services import create_campaign


def has_marketing_access(user):
    return user.is_authenticated and (
        user.is_staff or user.groups.filter(name__in=["Marketing Manager", "Marketing Staff"]).exists()
    )


marketing_access_required = user_passes_test(has_marketing_access, login_url="/accounts/login/")


@login_required
def dashboard(request):
    campaigns = Campaign.objects.all()[:5]
    return render(request, "campaigns/dashboard.html", {"campaigns": campaigns})


@marketing_access_required
def campaign_list(request):
    campaigns = Campaign.objects.all()
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if query:
        campaigns = campaigns.filter(name__icontains=query)
    if status:
        campaigns = campaigns.filter(status=status)
    return render(
        request,
        "campaigns/campaign_list.html",
        {"campaigns": campaigns, "query": query, "status": status, "status_choices": Campaign.Status.choices},
    )


@marketing_access_required
def campaign_create(request):
    form = CampaignForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        campaign = create_campaign(cleaned_data=form.cleaned_data, user=request.user)
        messages.success(request, "Đã tạo chiến dịch.")
        return redirect("campaigns:detail", pk=campaign.pk)
    return render(request, "campaigns/campaign_form.html", {"form": form, "title": "Tạo chiến dịch"})


@marketing_access_required
def campaign_update(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    form = CampaignForm(request.POST or None, instance=campaign)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Đã cập nhật chiến dịch.")
        return redirect("campaigns:detail", pk=campaign.pk)
    return render(request, "campaigns/campaign_form.html", {"form": form, "title": "Cập nhật chiến dịch"})


@marketing_access_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    return render(
        request,
        "campaigns/campaign_detail.html",
        {"campaign": campaign, "summary": campaign.performance_summary(), "contents": campaign.contents.all()},
    )


@marketing_access_required
def content_create(request, campaign_id):
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    form = ContentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        content = form.save(commit=False)
        content.campaign = campaign
        content.source = content.Source.MANUAL
        content.save()
        messages.success(request, "Đã lưu nội dung ở trạng thái bản nháp.")
        return redirect("campaigns:detail", pk=campaign.pk)
    return render(
        request,
        "campaigns/content_form.html",
        {"form": form, "campaign": campaign, "title": "Thêm nội dung"},
    )


@marketing_access_required
def ai_ideas(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Chỉ hỗ trợ POST."}, status=405)
    service = MarketingAIService()
    result = service.generate_content_ideas(
        campaign_brief=request.POST.get("campaign_brief", "").strip(),
        channel_name=request.POST.get("channel_name", "").strip() or "Facebook",
        tone=request.POST.get("tone", "thân thiện").strip() or "thân thiện",
    )
    return JsonResponse(result)
