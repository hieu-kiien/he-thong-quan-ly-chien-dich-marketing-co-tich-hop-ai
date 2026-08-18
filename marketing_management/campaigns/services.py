from django.db import transaction

from .models import Campaign


@transaction.atomic
def create_campaign(*, cleaned_data, user):
    campaign = Campaign(**cleaned_data, created_by=user)
    campaign.full_clean()
    campaign.save()
    return campaign
