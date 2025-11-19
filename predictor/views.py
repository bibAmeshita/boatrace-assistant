from __future__ import annotations

import json
from typing import Dict, Callable, Tuple, List

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from requests.adapters import HTTPAdapter, Retry

from today_race_detail.extractors.entry_table import extract_entries_from_racelist_html
from today_race_detail.extractors.race_meta import extract_race_meta_from_html

from .features import make_feature_table
from . import rules

JsonDict = Dict[str, object]
EntryList = List[Dict[str, object]]

_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.boatrace.jp/",
    "Accept-Language": "ja",
}

FUNC_MAP: Dict[Tuple[str, str], Callable[[EntryList, int], JsonDict]] = {
    ("3連単", "通常"): rules.make_trifecta_normal,
    ("3連単", "1軸流し"): rules.make_trifecta_1axle,
    ("3連単", "2軸流し"): rules.make_trifecta_2axle,
    ("3連単", "3艇ボックス"): rules.make_trifecta_box,
    ("3連単", "4艇ボックス"): rules.make_trifecta_box,
    ("3連単", "5艇ボックス"): rules.make_trifecta_box,
    ("2連単", "1軸流し"): rules.make_exacta_1axle,
    ("2連単", "ボックス"): rules.make_exacta_box,
    ("2連複", "1軸流し"): rules.make_quinella_1axle,
    ("2連複", "ボックス"): rules.make_quinella_box,
    ("3連複", "通常"): rules.make_trio_normal,
    ("3連複", "1軸流し"): rules.make_trio_1axle,
    ("3連複", "2軸流し"): rules.make_trio_2axle,
    ("3連複", "3艇ボックス"): rules.make_trio_box,
    ("3連複", "4艇ボックス"): rules.make_trio_box,
    ("3連複", "5艇ボックス"): rules.make_trio_box,
}


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(connect=3, read=3, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_race_detail(race_url: str) -> Tuple[JsonDict, EntryList]:
    """レースのHTMLを取得してmetaとentriesを返す"""
    session = _build_session()
    response = session.get(race_url, headers=_DEFAULT_HEADERS, timeout=20)
    response.raise_for_status()
    html = response.text
    meta = extract_race_meta_from_html(html, race_url)
    entries = extract_entries_from_racelist_html(html)
    return meta, entries


@csrf_exempt
def race_prediction(request):
    if request.method != "POST":
        return JsonResponse({"error": "POSTのみ対応しています"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSONの形式が不正です"}, status=400)

    race_url = payload.get("raceUrl")
    bet_type = payload.get("betType")
    method = payload.get("method")
    raw_points = payload.get("points", 5)

    if not race_url:
        return JsonResponse({"error": "raceUrl を指定してください"}, status=400)
    if not bet_type or not method:
        return JsonResponse({"error": "betType と method を指定してください"}, status=400)

    try:
        points = int(raw_points)
    except (TypeError, ValueError):
        return JsonResponse({"error": "points は整数で指定してください"}, status=400)

    try:
        meta, entries = fetch_race_detail(race_url)
    except requests.RequestException as exc:
        return JsonResponse({"error": f"レース情報の取得に失敗しました: {exc}"}, status=502)

    if not entries:
        return JsonResponse({"error": "出走表の取得に失敗しました"}, status=502)

    context = {
        "place": payload.get("place"),
        "distance": meta.get("distance"),
        "type": meta.get("type"),
    }

    scored_entries = make_feature_table(entries, context)
    func = FUNC_MAP.get((bet_type, method))
    if not func:
        return JsonResponse({"error": f"未対応方式: {bet_type} {method}"}, status=400)

    tickets = func(scored_entries, points)

    response_data = {
        "raceUrl": race_url,
        "betType": bet_type,
        "method": method,
        "points": points,
        "entries": scored_entries,
        "tickets": tickets,
    }

    # 依頼元の情報をそのまま転記（placeやraceなど）
    passthrough_keys = ["place", "race", "date", "memo"]
    for key in passthrough_keys:
        if key in payload:
            response_data[key] = payload[key]

    response_data.update(meta)

    return JsonResponse(response_data, json_dumps_params={"ensure_ascii": False})
