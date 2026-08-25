from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .ai_service import MarketingAIService
from .forms import CampaignForm, ChannelForm, ContentForm, MetricForm
from .models import Campaign, Channel, Content, Metric
from .services import create_campaign


def has_marketing_access(user):
    return user.is_authenticated and (
        user.is_staff or user.groups.filter(name__in=["Marketing Manager", "Marketing Staff"]).exists()
    )


marketing_access_required = user_passes_test(has_marketing_access, login_url="/accounts/login/")


def has_manager_access(user):
    return user.is_authenticated and (
        user.is_staff or user.groups.filter(name="Marketing Manager").exists()
    )


manager_access_required = user_passes_test(has_manager_access, login_url="/accounts/login/")


@marketing_access_required
def dashboard(request):
    campaigns = Campaign.objects.all()[:5]
    totals = Metric.objects.aggregate(
        impressions=Sum("impressions"),
        clicks=Sum("clicks"),
        conversions=Sum("conversions"),
        cost=Sum("cost"),
    )
    dashboard_summary = {
        "campaigns": Campaign.objects.count(),
        "active_campaigns": Campaign.objects.filter(status=Campaign.Status.ACTIVE).count(),
        "pending_review": Content.objects.filter(status=Content.Status.PENDING_REVIEW).count(),
        "impressions": totals["impressions"] or 0,
        "clicks": totals["clicks"] or 0,
        "conversions": totals["conversions"] or 0,
        "cost": totals["cost"] or 0,
    }
    return render(
        request,
        "campaigns/dashboard.html",
        {"campaigns": campaigns, "dashboard_summary": dashboard_summary},
    )


@marketing_access_required
def campaign_list(request):
    campaigns = Campaign.objects.all()
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    channel_id = request.GET.get("channel", "").strip()
    date_from_value = request.GET.get("date_from", "").strip()
    date_to_value = request.GET.get("date_to", "").strip()
    ordering = request.GET.get("sort", "-created_at").strip()
    allowed_ordering = {
        "-created_at": "Mới tạo trước",
        "name": "Tên A-Z",
        "-name": "Tên Z-A",
        "start_date": "Ngày bắt đầu tăng dần",
        "-start_date": "Ngày bắt đầu giảm dần",
        "budget": "Ngân sách tăng dần",
        "-budget": "Ngân sách giảm dần",
    }
    filter_errors = []
    date_from = None
    date_to = None
    if date_from_value:
        try:
            date_from = date.fromisoformat(date_from_value)
        except ValueError:
            filter_errors.append("Ngày bắt đầu lọc không hợp lệ.")
    if date_to_value:
        try:
            date_to = date.fromisoformat(date_to_value)
        except ValueError:
            filter_errors.append("Ngày kết thúc lọc không hợp lệ.")
    if date_from and date_to and date_from > date_to:
        filter_errors.append("Khoảng ngày lọc không hợp lệ.")
    if ordering not in allowed_ordering:
        ordering = "-created_at"
        filter_errors.append("Tiêu chí sắp xếp không hợp lệ; đã dùng mặc định.")
    if query:
        campaigns = campaigns.filter(
            Q(name__icontains=query)
            | Q(objective__icontains=query)
            | Q(product__icontains=query)
        )
    if status:
        campaigns = campaigns.filter(status=status)
    if channel_id:
        if channel_id.isdigit():
            campaigns = campaigns.filter(
                Q(contents__channel_id=int(channel_id)) | Q(metrics__channel_id=int(channel_id))
            ).distinct()
        else:
            filter_errors.append("Kênh lọc không hợp lệ.")
    if date_from and date_to:
        campaigns = campaigns.filter(end_date__gte=date_from, start_date__lte=date_to)
    elif date_from:
        campaigns = campaigns.filter(end_date__gte=date_from)
    elif date_to:
        campaigns = campaigns.filter(start_date__lte=date_to)
    campaigns = campaigns.order_by(ordering)
    if filter_errors:
        for error in filter_errors:
            messages.error(request, error)
    return render(
        request,
        "campaigns/campaign_list.html",
        {
            "campaigns": campaigns,
            "query": query,
            "status": status,
            "status_choices": Campaign.Status.choices,
            "channels": Channel.objects.filter(is_active=True),
            "channel_id": channel_id,
            "date_from": date_from_value,
            "date_to": date_to_value,
            "ordering": ordering,
            "ordering_choices": allowed_ordering.items(),
            "can_manage": has_manager_access(request.user),
        },
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


@manager_access_required
def campaign_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Chỉ hỗ trợ POST."}, status=405)
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.delete()
    messages.success(request, "Đã xóa chiến dịch và dữ liệu liên quan.")
    return redirect("campaigns:list")


@marketing_access_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    return render(
        request,
        "campaigns/campaign_detail.html",
        {
            "campaign": campaign,
            "summary": campaign.performance_summary(),
            "contents": campaign.contents.all(),
            "metrics": campaign.metrics.select_related("channel"),
            "can_approve": has_manager_access(request.user),
            "can_manage": has_manager_access(request.user),
        },
    )


@marketing_access_required
def channel_list(request):
    channels = Channel.objects.all()
    return render(
        request,
        "campaigns/channel_list.html",
        {"channels": channels, "can_manage": has_manager_access(request.user)},
    )


@marketing_access_required
def channel_create(request):
    form = ChannelForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Đã tạo kênh truyền thông.")
        return redirect("campaigns:channel-list")
    return render(request, "campaigns/channel_form.html", {"form": form, "title": "Thêm kênh truyền thông"})


@marketing_access_required
def channel_update(request, pk):
    channel = get_object_or_404(Channel, pk=pk)
    form = ChannelForm(request.POST or None, instance=channel)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Đã cập nhật kênh truyền thông.")
        return redirect("campaigns:channel-list")
    return render(request, "campaigns/channel_form.html", {"form": form, "title": "Cập nhật kênh truyền thông"})


@manager_access_required
def channel_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Chỉ hỗ trợ POST."}, status=405)
    channel = get_object_or_404(Channel, pk=pk)
    try:
        channel.delete()
    except ProtectedError:
        messages.error(request, "Không thể xóa kênh đang được chiến dịch hoặc metric sử dụng.")
    else:
        messages.success(request, "Đã xóa kênh truyền thông.")
    return redirect("campaigns:channel-list")


@marketing_access_required
def content_create(request, campaign_id):
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    form = ContentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        content = form.save(commit=False)
        content.campaign = campaign
        content.source = content.Source.MANUAL
        content.full_clean()
        content.save()
        messages.success(request, "Đã lưu nội dung ở trạng thái bản nháp.")
        return redirect("campaigns:detail", pk=campaign.pk)
    return render(
        request,
        "campaigns/content_form.html",
        {"form": form, "campaign": campaign, "title": "Thêm nội dung"},
    )


@marketing_access_required
def content_update(request, pk):
    content = get_object_or_404(Content, pk=pk)
    form = ContentForm(request.POST or None, instance=content)
    if request.method == "POST" and form.is_valid():
        updated_content = form.save(commit=False)
        updated_content.status = Content.Status.DRAFT
        updated_content.approved_by = None
        updated_content.approved_at = None
        updated_content.save()
        messages.success(request, "Đã cập nhật nội dung; nội dung cần được duyệt lại trước khi đăng.")
        return redirect("campaigns:detail", pk=updated_content.campaign_id)
    return render(
        request,
        "campaigns/content_form.html",
        {"form": form, "campaign": content.campaign, "title": "Cập nhật nội dung"},
    )


@manager_access_required
def content_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Chỉ hỗ trợ POST."}, status=405)
    content = get_object_or_404(Content, pk=pk)
    campaign_id = content.campaign_id
    content.delete()
    messages.success(request, "Đã xóa nội dung.")
    return redirect("campaigns:detail", pk=campaign_id)


@marketing_access_required
def metric_create(request, campaign_id):
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    form = MetricForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        metric = Metric(campaign=campaign, **form.cleaned_data)
        try:
            metric.full_clean()
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            metric.save()
            messages.success(request, "Đã ghi nhận metric.")
            return redirect("campaigns:detail", pk=campaign.pk)
    return render(request, "campaigns/metric_form.html", {"form": form, "campaign": campaign})


@marketing_access_required
def metric_update(request, pk):
    metric = get_object_or_404(Metric, pk=pk)
    form = MetricForm(request.POST or None, instance=metric)
    if request.method == "POST" and form.is_valid():
        updated_metric = form.save(commit=False)
        updated_metric.campaign = metric.campaign
        try:
            updated_metric.full_clean()
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            updated_metric.save()
            messages.success(request, "Đã cập nhật metric.")
            return redirect("campaigns:detail", pk=updated_metric.campaign_id)
    return render(
        request,
        "campaigns/metric_form.html",
        {"form": form, "campaign": metric.campaign, "title": "Cập nhật metric"},
    )


@manager_access_required
def metric_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Chỉ hỗ trợ POST."}, status=405)
    metric = get_object_or_404(Metric, pk=pk)
    campaign_id = metric.campaign_id
    metric.delete()
    messages.success(request, "Đã xóa metric.")
    return redirect("campaigns:detail", pk=campaign_id)


@manager_access_required
def content_approve(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Chỉ hỗ trợ POST."}, status=405)
    content = get_object_or_404(Content, pk=pk)
    content.approve(request.user)
    messages.success(request, "Đã duyệt nội dung.")
    return redirect("campaigns:detail", pk=content.campaign_id)


@manager_access_required
def content_reject(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Chỉ hỗ trợ POST."}, status=405)
    content = get_object_or_404(Content, pk=pk)
    content.reject()
    messages.success(request, "Đã từ chối nội dung; cần chỉnh sửa trước khi gửi lại.")
    return redirect("campaigns:detail", pk=content.campaign_id)


@manager_access_required
def content_publish(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Chỉ hỗ trợ POST."}, status=405)
    content = get_object_or_404(Content, pk=pk)
    content.publish()
    messages.success(request, "Đã chuyển nội dung sang trạng thái đã đăng.")
    return redirect("campaigns:detail", pk=content.campaign_id)


@marketing_access_required
def ai_ideas(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Chỉ hỗ trợ POST."}, status=405)
    campaign_brief = request.POST.get("campaign_brief", "").strip()
    if not campaign_brief:
        return JsonResponse({"detail": "campaign_brief là bắt buộc."}, status=400)
    service = MarketingAIService()
    result = service.generate_content_ideas(
        campaign_brief=campaign_brief,
        channel_name=request.POST.get("channel_name", "").strip() or "Facebook",
        tone=request.POST.get("tone", "thân thiện").strip() or "thân thiện",
    )
    return JsonResponse(result)
