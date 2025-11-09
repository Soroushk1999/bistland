import os
from celery import shared_task
from django.utils import timezone

from .models import Phone
from .mongo import _mongo_collection


@shared_task
def save_phone_in_sql_task(phone):
    saved_phone = Phone.objects.create(phone=phone)
    return saved_phone.id


@shared_task
def log_request_in_mongo_task(meta: dict):
    meta = {**meta, "ts": timezone.now().isoformat()}
    _mongo_collection().insert_one(meta)
