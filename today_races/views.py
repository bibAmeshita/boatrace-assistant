# today_races/views.py

from django.http import JsonResponse, HttpResponseBadRequest
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
from datetime import date
from .models import DailyRaceCache
import logging
logger = logging.getLogger(__name__)

INDEX_URL = "https://www.boatrace.jp/owpc/pc/race/index"
BASE = "https://www.boatrace.jp"

def api_root(request):
    return JsonResponse({
        "status": "ok",
        "endpoints": [
            "/api/today_races/all/",
        ]
    })


WEATHER_URL_DEFAULTS = {
    "桐生": "https://tenki.jp/leisure/horse/3/13/32948/1hour.html",
    "戸田": "https://tenki.jp/leisure/horse/3/14/32949/1hour.html",
    "江戸川": "https://tenki.jp/leisure/horse/3/16/32950/1hour.html",
    "平和島": "https://tenki.jp/leisure/horse/3/16/32951/1hour.html",
    "多摩川": "https://tenki.jp/leisure/horse/3/16/32952/1hour.html",
    "浜名湖": "https://tenki.jp/leisure/horse/5/25/32953/1hour.html",
    "蒲郡": "https://tenki.jp/leisure/horse/5/26/32954/1hour.html",
    "常滑": "https://tenki.jp/leisure/horse/5/26/32955/1hour.html",
    "津": "https://tenki.jp/leisure/horse/5/27/32956/1hour.html",
    "三国": "https://tenki.jp/leisure/horse/4/21/32957/1hour.html",
    "びわこ": "https://tenki.jp/leisure/horse/6/28/32958/1hour.html",
    "住之江": "https://tenki.jp/leisure/horse/6/30/32959/1hour.html",
    "尼崎": "https://tenki.jp/leisure/horse/6/31/32960/1hour.html",
    "鳴門": "https://tenki.jp/leisure/horse/8/39/32961/1hour.html",
    "丸亀": "https://tenki.jp/leisure/horse/8/40/32962/1hour.html",
    "児島": "https://tenki.jp/leisure/horse/7/36/32963/1hour.html",
    "宮島": "https://tenki.jp/leisure/horse/7/37/32964/1hour.html",
    "徳山": "https://tenki.jp/leisure/horse/7/38/32965/1hour.html",
    "下関": "https://tenki.jp/leisure/horse/7/38/32966/1hour.html",
    "若松": "https://tenki.jp/leisure/horse/9/43/32967/1hour.html",
    "芦屋": "https://tenki.jp/leisure/horse/9/43/32968/1hour.html",
    "福岡": "https://tenki.jp/leisure/horse/9/43/32969/1hour.html",
    "唐津": "https://tenki.jp/leisure/horse/9/44/32970/1hour.html",
    "大村": "https://tenki.jp/leisure/horse/9/45/32971/1hour.html",
}

# 🏁 今日の全レース取得（localStorage側でキャッシュ）
def all_races_today(request):
    if request.method != "GET":
        return HttpResponseBadRequest("GET only")

    from datetime import date
    from .models import DailyRaceCache
    import json

    today = date.today()
    cache = DailyRaceCache.objects.first()

    # ✅ 既存キャッシュがあって、今日ならそのまま返す
    if cache and cache.date == today:
        print("📦 今日のキャッシュを使用（再取得なし）")
        sites = json.loads(cache.json_text)
        return JsonResponse(sites, safe=False)

    # ⚡ ここから取得開始（キャッシュなし or 古い日付）

    res = requests.get(INDEX_URL, timeout=20)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    sites = []
    for tbody in soup.select(".table1 table > tbody"):
        try:
            place_img = tbody.select_one("tr td img[alt]")
            place = place_img.get("alt").strip() if place_img else None
            if not place:
                continue

            title_a = tbody.select_one('td.is-alignL.is-fBold.is-p10-7 a[href*="/owpc/pc/race/raceindex"]')
            if not title_a:
                continue

            title = title_a.get_text(strip=True)
            title_url = urljoin(BASE, title_a.get("href"))
            # races = fetch_races_from_raceindex(title_url)

            # 🎯 テスト用：racesを空にする（ここがポイント）
            races = []

            sites.append({
                "place": place,
                "title": title,
                "raceindex_url": title_url,
                "races": races,
            })
        except Exception as e:
            print("Error parsing site:", e)

    # ✅ 第一段階のJSON保存テスト
    #json_text = json.dumps(sites, ensure_ascii=False, indent=2)
    #with open("test_all_races_today.json", "w", encoding="utf-8") as f:
    #    f.write(json_text)


    # ✅ 完全版取得開始
    for site in sites:
        try:
            site["races"] = fetch_races_from_raceindex(site["raceindex_url"])
            print(f"🏁 {site['place']}: {len(site['races'])} races 取得")
        except Exception as e:
            print(f"⚠️ {site['place']} のレース詳細取得に失敗: {e}")

    # ✅ 完全版取得開始
    for site in sites:
        try:
            site["races"] = fetch_races_from_raceindex(site["raceindex_url"])
            print(f"🏁 {site['place']}: {len(site['races'])} races 取得")
        except Exception as e:
            print(f"⚠️ {site['place']} のレース詳細取得に失敗: {e}")

    # 🌤 各開催場に天気をマージ
    for site in sites:
        try:
            merge_weather_into_races(site)
        except Exception as e:
            logger.warning(f"[weather] {site.get('place')} への天気付与に失敗: {e}")

    # 💾 JSONをファイル保存（テスト用）
    #json_text = json.dumps(sites, ensure_ascii=False, indent=2)
    #with open("test_all_races_today_full.json", "w", encoding="utf-8") as f:
    #    f.write(json_text)


    # 💾 DBに上書き（常に1件）
    json_text = json.dumps(sites, ensure_ascii=False)
    if cache:
        cache.date = today
        cache.json_text = json_text
        cache.save(update_fields=["date", "json_text", "updated_at"])
        #print(f"💾 既存データを上書き保存 ({today})")
    else:
        DailyRaceCache.objects.create(date=today, json_text=json_text)
        #print(f"🆕 新規保存 ({today})")

    return JsonResponse(sites, safe=False)


# 🏁 各会場別のレース情報を取得
def fetch_races_from_raceindex(url):
    """各レース場のレース一覧（1R〜12R）を取得"""
    res = requests.get(url, timeout=20)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    races = []
    rows = soup.select(".contentsFrame1_inner .table1 table tbody tr")
    for row in rows:
        try:
            rno = row.select_one("td.is-fBold a").text.strip()
            time = row.select_one("td:nth-of-type(2)").text.strip()
            racelist_link = row.select_one('ul.textLinks3 a[href*="racelist"]')
            race_url = urljoin(BASE, racelist_link["href"]) if racelist_link else None

            races.append({
                "rno": rno,
                "time": time,
                "url": race_url,
            })
        except Exception as e:
            print("Error parsing race:", e)

    return races


# ☀️ 各会場の天気を天気予報から取得
def fetch_weather_for_place(place: str):
    """
    tenki.jp から 1時間ごとの天気・風を 1〜24 時の dict で返す。
    返り値: { hour(int): {"weather": "曇り", "direction": "北西", "speed": 4}, ... }
    """
    url = WEATHER_URL_DEFAULTS.get(place)
    if not url:
        logger.warning(f"[weather] URL not found for place={place}")
        return {}

    try:
        res = requests.get(url, timeout=15)
        res.encoding = "utf-8"
    except Exception as e:
        logger.warning(f"[weather] request error for {place}: {e}")
        return {}

    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.select_one("#forecast-point-1h-today")
    if not table:
        logger.warning(f"[weather] table not found for {place}")
        return {}

    # 時刻（01〜24）
    hour_cells = table.select("tr.hour td span")
    # 天気（曇り / 晴れ …）
    weather_cells = table.select("tr.weather td p")
    # 風向（北西 / 東北東 …）
    dir_cells = table.select("tr.wind-blow td p")
    # 風速（1 / 4 / 7 …）
    speed_cells = table.select("tr.wind-speed td span")

    n = min(len(hour_cells), len(weather_cells), len(dir_cells), len(speed_cells))
    result = {}

    for i in range(n):
        try:
            hour = int(hour_cells[i].get_text(strip=True))  # 1〜24
        except ValueError:
            continue

        weather = weather_cells[i].get_text(strip=True)
        direction = dir_cells[i].get_text(strip=True)
        speed_text = speed_cells[i].get_text(strip=True)

        try:
            speed = int(speed_text)
        except ValueError:
            speed = None

        result[hour] = {
            "weather": weather,
            "direction": direction,
            "speed": speed,
        }

    return result

# ☀️ 天気予報を各レースの日時の箇所に結合
def merge_weather_into_races(site: dict):
    """
    site = {"place": ..., "races": [...]}
    各レースの time から hour を取り出して、weather / wind を追加する。
    """
    place = site.get("place")
    if not place:
        return

    weather_map = fetch_weather_for_place(place)
    if not weather_map:
        return

    for race in site.get("races", []):
        time_str = race.get("time")
        if not time_str:
            continue

        try:
            hour = int(time_str.split(":")[0])  # "08:35" → 8
        except Exception:
            continue

        info = weather_map.get(hour)
        if not info:
            continue

        race["weather"] = info["weather"]

        if info["speed"] is not None:
            race["wind"] = f"{info['direction']}{info['speed']}m"
        else:
            race["wind"] = info["direction"]

#def characters_api(request):
#    from ui.models import Character
#    characters = list(Character.objects.values("id", "name", "tone", "prediction", "index"))
#    return JsonResponse(characters, safe=False)