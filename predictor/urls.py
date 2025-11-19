from django.urls import path

from .views import race_prediction

urlpatterns = [
    path("", race_prediction, name="race_prediction"),
]
