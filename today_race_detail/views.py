# today_race_detail/views.py
import json
import os
from datetime import datetime

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from requests.adapters import HTTPAdapter, Retry

from .extractors.race_meta import extract_race_meta_from_html
from .extractors.entry_table import extract_entries_from_racelist_html
from .extractors.entry_table_just import (
    extract_entries_from_racelist_just_html,
    extract_weather_meta_from_html,
    extract_before_entries_from_html,
)
from today_race_detail.features.feature_calculator_a import make_feature_table
from today_race_detail.features.feature_calculator_b import make_feature_table_just

TEST_MODE = True  # ★ テストするときだけ True、本番は False


# ==========================================================
# A/B 共通：racelist → meta / entries 抽出 → 時間で分岐
# ==========================================================
@csrf_exempt
def get_race_detail(request):
    print("✅ レース情報取得開始（共通：A/B前処理）")

    # ---------------------------
    # ① posted の取得
    # ---------------------------
    if request.method != "POST":
        if TEST_MODE:
            print("⚠️ テストモード：固定データで処理します")
            posted = {
                "raceUrl": "https://www.boatrace.jp/owpc/pc/race/racelist?rno=12&jcd=24&hd=20251120",
                "place": "多摩川",
                "raceNo": "12R",
                "time": "22:41",
            }
        else:
            return JsonResponse({"error": "POSTだけです"}, status=400)
    else:
        try:
            posted = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON が不正です"}, status=400)

    race_url = posted.get("raceUrl")
    race_time_str = posted.get("time")

    if not race_url:
        return JsonResponse({"error": "raceUrl がありません"}, status=400)
    if not race_time_str:
        return JsonResponse({"error": "time がありません"}, status=400)

    # ---------------------------
    # ② racelist HTML 取得（ここだけで1回だけ）
    # ---------------------------
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

    # ---------------------------
    # ③ meta / entries 抽出
    # ---------------------------
    meta = extract_race_meta_from_html(html, race_url)
    trimmed_meta = {
        "date_text": meta.get("date_text"),
        "day_text": meta.get("day_text"),
        "type": meta.get("type"),
        "distance": meta.get("distance"),
    }

    # A 用（通常）
    entries_for_a = extract_entries_from_racelist_html(html)

    # B 用（直前版）
    entries_for_b = extract_entries_from_racelist_just_html(html)

    # ---------------------------
    # ④ A/B 時間判定
    # ---------------------------
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    race_dt = datetime.strptime(f"{today_str} {race_time_str}", "%Y-%m-%d %H:%M")
    diff_min = (race_dt - now).total_seconds() / 60

    print(f"⏱ 現在: {now}, レース: {race_dt}, diff_min = {diff_min:.2f}")

    # ---------------------------
    # A：15分以上前（事前）
    # ---------------------------
    if diff_min > 15:
        print("🟢 Aモード（事前予想）")

        context = {
            "place": posted.get("place"),
            "distance": trimmed_meta.get("distance"),
            "type": trimmed_meta.get("type"),
        }

        # 事前スコア付与
        scored_entries = make_feature_table(entries_for_a, context)

        # B と同じ構造に合わせる
        full_data = {**posted, **trimmed_meta, "entries": scored_entries}

        # B と同じ買い目ロジックへ
        result = run_race_predict_logic(full_data)
        result["mode"] = "A"

        return JsonResponse(result, safe=False)

    # ---------------------------
    # B：15分以内（直前）
    # ---------------------------
    print("🔵 Bモード（直前予想）")

    result = _run_race_detail_just_logic(
        posted=posted,
        trimmed_meta=trimmed_meta,
        entries=entries_for_b,
    )
    return JsonResponse(result, safe=False)



# ==========================================================
# B専用：beforeinfo / weather をマージして買い目10点へ
# ==========================================================
def _run_race_detail_just_logic(posted, trimmed_meta, entries):

    race_url = posted.get("raceUrl")

    # --- beforeinfo ---
    session = requests.Session()
    retry = Retry(connect=3, read=3, backoff_factor=1.0)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.boatrace.jp/", "Accept-Language": "ja"}

    beforeinfo_url = race_url.replace("racelist", "beforeinfo")

    weather_meta = {}
    before_entries = {}

    try:
        res2 = session.get(beforeinfo_url, headers=headers, timeout=20)
        res2.raise_for_status()
        before_html = res2.text

        if before_html.strip() and "該当するレース情報はありません" not in before_html:
            weather_meta = extract_weather_meta_from_html(before_html)
            before_entries = extract_before_entries_from_html(before_html)
    except Exception as e:
        before_entries = {}
        weather_meta = {}

    # --- entries に直前展示情報を統合 ---
    for e in entries:
        lane = int(e.get("lane", 0))
        if lane in before_entries:
            e.update(before_entries[lane])

    # --- full データにまとめる ---
    full_data = {**posted, **trimmed_meta, **weather_meta, "entries": entries}

    # --- 直前ロジック（買い目10点） ---
    return run_race_predict_logic(full_data)



# スコア順の3連単10点
def run_race_predict_logic(data):
    """
    直前データにスコア付与 → 参考3連単10点 → return data
    A/B どちらからも使える “共通ロジック” として配置
    """

    try:
        print("💥 直前ロジック開始")

        # ---------------------------
        # entries + context
        # ---------------------------
        entries = data.get("entries", [])
        context = {
            "place": data.get("place"),
            "distance": data.get("distance"),
            "type": data.get("type"),
        }

        # ---------------------------
        # スコア付与（直前）
        # ---------------------------
        new_entries = make_feature_table_just(entries, context)
        data["entries"] = new_entries

        # ---------------------------
        # 参考3連単10点 作成
        # ---------------------------
        def make_reference_trifecta(entries, points=10):
            if not entries or len(entries) < 3:
                return []

            from itertools import permutations

            # スコア順
            sorted_entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)

            # 上位6艇
            lanes = [e["lane"] for e in sorted_entries[:6]]
            combos = list(permutations(lanes, 3))

            # スコア合計でソート
            score_map = {e["lane"]: e["score"] for e in sorted_entries}
            combos.sort(
                key=lambda t: score_map[t[0]] + score_map[t[1]] + score_map[t[2]],
                reverse=True,
            )

            return [f"{a}-{b}-{c}" for a, b, c in combos[:points]]

        # 参考買い目セット
        data["reference_picks"] = make_reference_trifecta(new_entries, points=10)

        return data

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}