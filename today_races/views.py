from django.http import JsonResponse, HttpResponseBadRequest
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from django.http import JsonResponse
from ui.models import Character

INDEX_URL = "https://www.boatrace.jp/owpc/pc/race/index"
BASE = "https://www.boatrace.jp"

def fetch_today_sites(request):

    if request.method != "GET":
        return HttpResponseBadRequest("GET only")

    res = requests.get(INDEX_URL, timeout=15)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    out = []

    # tbodyごとに抽出
    for tbody in soup.select(".table1 table > tbody"):
        try:
            place_img = tbody.select_one("tr td img[alt]")
            place = place_img.get("alt").strip() if place_img else None
            if not place:
                continue

            title_a = tbody.select_one(
                'td.is-alignL.is-fBold.is-p10-7 a[href*="/owpc/pc/race/raceindex"]'
            )
            if not title_a:
                continue

            title = title_a.get_text(strip=True)
            title_url = urljoin(BASE, title_a.get("href"))

            out.append({
                "place": place,
                "title": title,
                "raceindex_url": title_url,
            })
        except:
            continue

    return JsonResponse(out, safe=False)

def fetch_race_list_api(request):
    raceindex_url = request.GET.get("url")
    if not raceindex_url:
        return HttpResponseBadRequest("url param required")

    print("🔥 fetch_race_list_api called:", raceindex_url)

    races = fetch_races_from_raceindex(raceindex_url)
    return JsonResponse(races, safe=False)

def fetch_all_races_today_api(request):
    # 1) 本日の開催地一覧を取得
    sites = fetch_today_sites(request).content
    import json
    sites = json.loads(sites)

    result = []

    # 2) 各開催地についてレース一覧を取得
    for site in sites:
        raceindex_url = site["raceindex_url"]
        races = fetch_races_from_raceindex(raceindex_url)

        result.append({
            "place": site["place"],
            "title": site["title"],
            "raceindex_url": raceindex_url,
            "races": races
        })

    return JsonResponse(result, safe=False)

def fetch_all_races_today_api(request):
    if request.method != "GET":
        return HttpResponseBadRequest("GET only")

    # 今日の開催一覧を取得
    sites = fetch_today_sites(request).content
    import json
    sites = json.loads(sites)

    result = []

    for site in sites:
        url = site.get("raceindex_url")
        races = fetch_races_from_raceindex(url)  # レース一覧取得
        site["races"] = races  # 合体
        result.append(site)

    return JsonResponse(result, safe=False)

def fetch_races_from_raceindex(url):
    """各レース場のレース一覧（1R〜12R）を取得"""
    res = requests.get(url)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    races = []
    rows = soup.select(".contentsFrame1_inner .table1 table tbody tr")

    for row in rows:
        try:
            rno = row.select_one("td.is-fBold a").text.strip()
            time = row.select_one("td:nth-of-type(2)").text.strip()
            racelist_link = row.select_one('ul.textLinks3 a[href*="racelist"]')

            race_url = (
                "https://www.boatrace.jp" + racelist_link["href"]
                if racelist_link else None
            )

            races.append({
                "rno": rno,
                "time": time,
                "url": race_url
            })
        except Exception as e:
            print("Error parsing row:", e)

    return races

def get_today_races():
    url = "https://www.boatrace.jp/owpc/pc/race/index"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    races = []
    for item in soup.select(".tab01_body a"):
        title = item.text.strip()
        href = item.get("href")
        if href:
            races.append({
                "title": title,
                "url": f"https://www.boatrace.jp{href}"
            })

    print("✅ get_today_races:", races)
    return races

def today_races_api(request):
    return fetch_today_sites(request)

def characters_api(request):
    characters = list(Character.objects.values("id", "name", "tone", "prediction", "index"))
    return JsonResponse(characters, safe=False)