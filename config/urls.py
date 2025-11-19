from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from ui.views import home, config, prediction_1,  prediction_2, media, delete_media, result, delete_result, report
from today_races import views as tr_views
from today_race_detail.views import get_race_detail
from django.http import JsonResponse

def api_root(request):
    return JsonResponse({
        "status": "ok",
        "endpoints": [
            "/api/today_races/all/",
            "/api/today_races/characters_api/",
        ]
    })


urlpatterns = [
    path('admin/', admin.site.urls),

    # メイン画面
    path('', home, name='home'),

    # メディア
    path('media/', media, name='media'),
    path('media/delete/<int:pk>/', delete_media, name='delete_media'),

    # 結果
    path('result/', result, name='result'),
    path('result/delete/<int:pk>/', delete_result, name='delete_result'),

    # 設定・予測
    path('config/', config, name='config'),
    path('prediction-1/', prediction_1, name='prediction_1'),
    path('prediction-2/', prediction_2, name='prediction_2'),

    # 🏁 今日のレース関連API（localStorage方式）
    path("all_races_today/", tr_views.all_races_today, name="all_races_today"),
    path("characters_api/", tr_views.characters_api, name="characters_api"),

    # 各アプリ include
    path("today_race_detail/", include("today_race_detail.urls")),
    path("predictor_2/", include("predictor_2.urls")),
    path("report/", include("report.urls")),

    #API
    path("api/", api_root),
    path("api/today_races/", include("today_races.urls")),
    path("api/race/", include("predictor.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)