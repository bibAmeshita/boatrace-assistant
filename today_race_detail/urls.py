# today_race_detail/urls.py
from django.urls import path
from .views import get_race_detail

urlpatterns = [
    path("", get_race_detail, name="get_race_detail"),
]