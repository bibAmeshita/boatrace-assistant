import json, os
from datetime import datetime
from django.http import JsonResponse
from .extractors.race_meta import extract_race_meta_from_html
from .extractors.entry_table import extract_entries_from_racelist_html
import requests
from requests.adapters import HTTPAdapter, Retry
from django.views.decorators.csrf import csrf_exempt
from predictor_1.features import make_feature_table

@csrf_exempt
def get_race_detail(request):
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
    race_no = posted.get("race", "unknown")

    filename = f"{save_dir}/race_detail_{today}_{race_no}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {filename}")

    return JsonResponse(output, json_dumps_params={"ensure_ascii": False})

    body = json.loads(request.body)
    data = body

    entries = data.get("entries", [])
    context = {
        "place": data.get("place"),
        "distance": data.get("distance"),
        "type": data.get("type"),
    }

    new_entries = make_feature_table(entries, context)
    data["entries"] = new_entries

    # ===== JSON 保存 =====
    save_dir = "data"
    os.makedirs(save_dir, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    race_no = data.get("race", "unknown")

    filename = f"{save_dir}/race_detail_{today}_{race_no}_scored.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Scored JSON saved: {filename}")

    return JsonResponse(data, json_dumps_params={"ensure_ascii": False})