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
    logger.info("🐍 boatrace.jp からデータ取得開始")

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


def characters_api(request):
    from ui.models import Character
    characters = list(Character.objects.values("id", "name", "tone", "prediction", "index"))
    return JsonResponse(characters, safe=False)