# today_races/urls.py
from django.urls import path
from .views import fetch_today_sites
from . import views

urlpatterns = [
    path('fetch/', fetch_today_sites, name='today_races_fetch'),
    path('today_races_api/', views.today_races_api, name='today_races_api'),
    path("all/", views.all_races_today, name="all_races_today"),
]