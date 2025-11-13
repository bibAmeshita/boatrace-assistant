from django.urls import path
from . import views

urlpatterns = [
    path("", views.report, name="report"),
    path("save-report/", views.save_report, name="save_report"),
]