# today_race_detail/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.get_race_detail, name="get_race_detail"),
    path("save/", views.get_race_detail, name="save_race_detail"),
    path("just/", views.get_race_detail_just, name="save_race_detai_just"),
]