from django.db import models
from django.utils import timezone
import json

class DailyRaceCache(models.Model):
    date = models.DateField(unique=True)
    json_text = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_today(cls):
        today = timezone.localdate()
        obj, created = cls.objects.get_or_create(date=today)
        return obj

    @classmethod
    def save_today(cls, data_dict):
        today = timezone.localdate()
        text = json.dumps(data_dict, ensure_ascii=False)
        obj, _ = cls.objects.update_or_create(date=today, defaults={"json_text": text})
        return obj