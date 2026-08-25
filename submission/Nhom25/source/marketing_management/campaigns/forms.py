from django import forms

from .models import Campaign, Channel, Content, Metric


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["name", "objective", "audience", "product", "start_date", "end_date", "budget", "status"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "objective": forms.Textarea(attrs={"rows": 3}),
            "audience": forms.Textarea(attrs={"rows": 3}),
        }


class ChannelForm(forms.ModelForm):
    class Meta:
        model = Channel
        fields = ["name", "channel_type", "is_active"]


class ContentForm(forms.ModelForm):
    scheduled_at = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
    )

    class Meta:
        model = Content
        fields = ["channel", "title", "body", "content_type", "scheduled_at"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 8}),
        }


class MetricForm(forms.ModelForm):
    class Meta:
        model = Metric
        fields = ["channel", "metric_date", "impressions", "clicks", "conversions", "cost"]
        widgets = {"metric_date": forms.DateInput(attrs={"type": "date"})}
