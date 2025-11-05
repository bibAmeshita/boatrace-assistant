from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from ui.views import home, config, prediction_1
from today_races import views as tr_views
from today_race_detail.views import get_race_detail

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('config', config, name='config'),
    path('prediction-1/', prediction_1, name='prediction_1'),
    path("today_races_api/", tr_views.fetch_today_sites, name="today_races_api"),
    path("race_list_api/", tr_views.fetch_race_list_api, name="race_list_api"),
    path("all_races_today/", tr_views.fetch_all_races_today_api, name="all_races_today_api"),
    path("characters_api/", tr_views.characters_api, name="characters_api"),
    path("today_race_detail/", include("today_race_detail.urls")),
    path("", include("predictor_1.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)