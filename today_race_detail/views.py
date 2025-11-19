# today_race_detail/views.py
import json, os
from datetime import datetime
from django.http import JsonResponse
from .extractors.race_meta import extract_race_meta_from_html
from .extractors.entry_table import extract_entries_from_racelist_html
from .extractors.entry_table_just import extract_entries_from_racelist_just_html
import requests
from requests.adapters import HTTPAdapter, Retry
from django.views.decorators.csrf import csrf_exempt
from predictor_1.features import make_feature_table
from predictor_2.features import make_feature_table_just
from predictor_2.views import run_race_predict_logic

from .extractors.race_meta import extract_race_meta_from_html
from .extractors.entry_table_just import (
    extract_entries_from_racelist_just_html,
    extract_weather_meta_from_html,
    extract_before_entries_from_html,
)

from bs4 import BeautifulSoup

# 事前予想の前処理
@csrf_exempt
def get_race_detail(request):
    print(f"✅事前予想用の取得開始")

    if request.method != "POST":
        return JsonResponse({"error": "POSTだけです"}, status=400)

    posted = json.loads(request.body)
    race_url = posted.get("raceUrl")
    if not race_url:
        return JsonResponse({"error": "raceUrl がありません"}, status=400)

    # HTML取得
    session = requests.Session()
    retry = Retry(connect=3, read=3, backoff_factor=1.0)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.boatrace.jp/",
        "Accept-Language": "ja",
    }
    res = session.get(race_url, headers=headers, timeout=20)
    res.raise_for_status()
    html = res.text

    # meta（必要ぶんだけ）
    meta = extract_race_meta_from_html(html, race_url)
    trimmed_meta = {
        "date_text": meta.get("date_text"),
        "day_text": meta.get("day_text"),
        "type": meta.get("type"),
        "distance": meta.get("distance"),
    }

    # entries（6艇）
    entries = extract_entries_from_racelist_html(html)

    # 合体
    output = {
        **posted,
        **trimmed_meta,
        "entries": entries,
    }

    # === ✅ スコア付与ここでやる ===
    context = {
        "place": output.get("place"),
        "distance": output.get("distance"),
        "type": output.get("type"),
    }
    scored_entries = make_feature_table(output["entries"], context)
    output["entries"] = scored_entries

    # ===== JSON 保存（スコア入り） =====
    save_dir = "data"
    os.makedirs(save_dir, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    place = posted.get("place", "unknown")
    race_no = posted.get("race", "unknown")

    # ✅ 地名を含めて統一
    filename = f"{save_dir}/race_detail_{place}_{today}_{race_no}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {filename}")

    return JsonResponse(output, json_dumps_params={"ensure_ascii": False})

# 直前予想の前処理
@csrf_exempt
def get_race_detail_just(request):
    print(f"✅直前予想用の取得開始")

    if request.method != "POST":
        return JsonResponse({"error": "POSTだけです"}, status=400)

    # === 📨 POSTデータ取得 ===
    posted = json.loads(request.body)
    race_url = posted.get("raceUrl")
    if not race_url:
        return JsonResponse({"error": "raceUrl がありません"}, status=400)

    # === 🌐 HTML取得設定 ===
    session = requests.Session()
    retry = Retry(connect=3, read=3, backoff_factor=1.0)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.boatrace.jp/",
        "Accept-Language": "ja",
    }

    # === 🏁 racelist ページ取得 ===
    res = session.get(race_url, headers=headers, timeout=20)
    res.raise_for_status()
    html = res.text

    # === 📋 基本情報抽出 ===
    meta = extract_race_meta_from_html(html, race_url)
    trimmed_meta = {
        "date_text": meta.get("date_text"),
        "day_text": meta.get("day_text"),
        "type": meta.get("type"),
        "distance": meta.get("distance"),
    }
    entries = extract_entries_from_racelist_just_html(html)

    # === 🌤 beforeinfo ページ取得 ===
    beforeinfo_url = race_url.replace("racelist", "beforeinfo")
    weather_meta = {}
    before_entries = {}

    try:
        res2 = session.get(beforeinfo_url, headers=headers, timeout=20)
        res2.raise_for_status()
        before_html = res2.text

        if not before_html.strip() or "該当するレース情報はありません" in before_html:
            # ページが存在しない／未開催
            before_entries = {}
            weather_meta = {}
            _save_debug("beforeinfo_missing.html", before_html)
        else:
            # 正常抽出
            weather_meta = extract_weather_meta_from_html(before_html)
            before_entries = extract_before_entries_from_html(before_html)
            _save_debug("beforeinfo_raw.html", before_html)
            _save_debug("before_entries.json", before_entries)

    except Exception as e:
        before_entries = {}
        weather_meta = {}
        _save_debug("beforeinfo_error.json", {"error": str(e)})

    # === 🧩 entries に直前情報を統合 ===
    for e in entries:
        lane = int(e.get("lane", 0))
        if lane in before_entries:
            e.update(before_entries[lane])

    # === 📦 全データ統合 ===
    output = {**posted, **trimmed_meta, **weather_meta, "entries": entries}

    # === ✅ スコア、買い目、コメント付与 ===
    result = run_race_predict_logic(output)
    return JsonResponse(result, safe=False)

    # === 💾 保存（スコア付き） ===
    save_dir = "data"
    os.makedirs(save_dir, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    place = posted.get("place", "unknown")
    race_no = posted.get("race", "unknown")
    filename = f"{save_dir}/race_detail_{place}_{today}_{race_no}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    _save_debug("final_output.json", output)
    return JsonResponse(output, json_dumps_params={"ensure_ascii": False})


# === 🧰 デバッグ保存ユーティリティ ===
def _save_debug(name: str, data):
    """printが無効な環境向け：JSONやHTMLをファイルに記録"""
    os.makedirs("data/logs", exist_ok=True)
    path = os.path.join("data/logs", name)
    mode = "w" if not name.endswith(".html") else "w"
    with open(path, mode, encoding="utf-8") as f:
        if name.endswith(".html"):
            f.write(data)
        else:
            json.dump(data, f, ensure_ascii=False, indent=2)
