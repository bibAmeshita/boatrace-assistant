from django.urls import path
from .views import race_predict

urlpatterns = [
    path("race_predict/", race_predict),
]