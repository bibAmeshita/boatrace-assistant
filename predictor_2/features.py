# predictor_2/features.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple
import re

Number = float

# ===== 欠損時の安全デフォルト =====
SAFE_DEFAULTS = {
    "lane": 3.5,              # 中枠平均
    "avg_st": 0.18,
    "national_win": 5.0,
    "local_win": 4.8,
    "national_2r": 33.0,
    "local_2r": 32.0,
    "motor_2r": 30.0,
    "boat_2r": 30.0,
    "national_3r": 50.0,
    "local_3r": 48.0,
    "motor_3r": 45.0,
    "boat_3r": 45.0,
    "weight": 52.5,
}

# ===== 場補正（1〜6枠別） =====
PLACE_BIAS = {
    "桐生":   {1:+0.8, 2:+0.4, 3:+0.1, 4:-0.2, 5:-0.5, 6:-0.7},
    "戸田":   {1:-0.3, 2:-0.2, 3:+0.1, 4:+0.4, 5:+0.6, 6:+0.8},
    "江戸川": {1:-0.5, 2:-0.2, 3:+0.2, 4:+0.4, 5:+0.6, 6:+0.8},
    "多摩川": {1:+1.0, 2:+0.5, 3:+0.2, 4:-0.2, 5:-0.5, 6:-0.8},
    "平和島": {1:+0.2, 2:+0.1, 3:0.0, 4:-0.2, 5:-0.4, 6:-0.6},
    "浜名湖": {1:+0.5, 2:+0.3, 3:+0.1, 4:-0.1, 5:-0.3, 6:-0.5},
    "蒲郡":   {1:+0.4, 2:+0.2, 3:+0.1, 4:-0.1, 5:-0.3, 6:-0.5},
    "常滑":   {1:+0.6, 2:+0.3, 3:+0.1, 4:-0.1, 5:-0.4, 6:-0.6},
    "津":     {1:+0.7, 2:+0.4, 3:+0.2, 4:-0.1, 5:-0.4, 6:-0.7},
    "びわこ": {1:-0.1, 2:+0.1, 3:+0.2, 4:+0.3, 5:+0.4, 6:+0.6},
    "三国":   {1:+0.8, 2:+0.5, 3:+0.2, 4:-0.1, 5:-0.4, 6:-0.7},
    "住之江": {1:+0.9, 2:+0.6, 3:+0.3, 4:0.0, 5:-0.3, 6:-0.6},
    "尼崎":   {1:+0.8, 2:+0.5, 3:+0.2, 4:-0.2, 5:-0.5, 6:-0.8},
    "鳴門":   {1:+0.5, 2:+0.2, 3:0.0, 4:-0.2, 5:-0.4, 6:-0.6},
    "丸亀":   {1:+0.8, 2:+0.5, 3:+0.2, 4:-0.1, 5:-0.4, 6:-0.6},
    "児島":   {1:+0.7, 2:+0.4, 3:+0.1, 4:-0.1, 5:-0.3, 6:-0.5},
    "宮島":   {1:+0.7, 2:+0.4, 3:+0.1, 4:-0.1, 5:-0.3, 6:-0.5},
    "徳山":   {1:+1.0, 2:+0.6, 3:+0.3, 4:-0.2, 5:-0.6, 6:-1.0},
    "下関":   {1:+0.9, 2:+0.6, 3:+0.3, 4:0.0, 5:-0.3, 6:-0.6},
    "若松":   {1:+0.8, 2:+0.5, 3:+0.2, 4:0.0, 5:-0.3, 6:-0.5},
    "芦屋":   {1:+0.9, 2:+0.6, 3:+0.3, 4:-0.1, 5:-0.4, 6:-0.7},
    "唐津":   {1:+0.8, 2:+0.5, 3:+0.2, 4:-0.1, 5:-0.3, 6:-0.5},
    "大村":   {1:+1.0, 2:+0.6, 3:+0.2, 4:-0.1, 5:-0.4, 6:-0.7},
    "福岡":  {1:+0.7, 2:+0.4, 3:+0.2, 4:0.0, 5:-0.3, 6:-0.5},
}

PLACE_GROUPS = {
    "イン強": ["徳山", "芦屋", "大村", "唐津", "若松"],
    "センター伸び": ["桐生", "蒲郡", "浜名湖", "鳴門"],
    "アウト伸び": ["戸田", "江戸川", "びわこ"],
    "フラット": ["多摩川", "下関", "常滑", "福岡", "丸亀", "児島", "平和島", "住之江", "宮島", "津", "尼崎"],
}

# ===== レース種別×階級バイアス =====
TYPE_BIAS = {
    "一般":      {"A1": 0.0,  "A2": 0.0,  "B1": 0.0,  "B2": 0.0},
    "予選":      {"A1": 0.1,  "A2": 0.05, "B1": 0.0,  "B2": 0.0},
    "準優勝戦":  {"A1": 0.5,  "A2": 0.3,  "B1": 0.1,  "B2": 0.0},
    "優勝戦":    {"A1": 1.0,  "A2": 0.5,  "B1": 0.2,  "B2": 0.0},
}

# ===== 共通関数 =====
def _to_float(v: Any, default: Number, key: str = "") -> Number:
    try:
        if v in (None, "", "-", "--"):
            return default
        val = float(str(v).replace("%", "").strip())
        # 連対率が異常に低い場合は欠損扱い
        if ("2r" in key or "3r" in key) and val < 5.0:
            return default
        return val
    except Exception:
        return default

def _safe_minmax(vals: List[Number]) -> Tuple[Number, Number]:
    clean = [v for v in vals if isinstance(v, (int, float))]
    if not clean:
        return 0.0, 1.0
    lo, hi = min(clean), max(clean)
    if lo == hi:
        hi = lo + (abs(lo) if lo != 0 else 1.0)
    return lo, hi

def _norm_direct(x: Number, lo: Number, hi: Number) -> Number:
    return (x - lo) / (hi - lo) if hi != lo else 0.5

def _norm_inverse(x: Number, lo: Number, hi: Number) -> Number:
    return (hi - x) / (hi - lo) if hi != lo else 0.5

def _distance_to_int(distance_text: str | None) -> int | None:
    if not distance_text:
        return None
    m = re.search(r"(\d+)", str(distance_text))
    return int(m.group(1)) if m else None

# ===== 動的場補正（天候・風向・波高対応） =====
def _dynamic_place_bias(
    place: str | None,
    wind_speed: float = 0.0,
    wind_angle: float = 0.0,
    wave_height: float = 0.0,
    temperature: float = 15.0
) -> Dict[int, float]:
    """
    各会場における「動的場補正」。
    風向・風速・波高・気温などの気象条件に基づき、
    枠ごとの補正値（+有利 / -不利）を返す。
    """

    # --- 基本補正 ---
    base_bias = PLACE_BIAS.get(place, {i: 0.0 for i in range(1, 7)}).copy()
    if not place or wind_speed == 0:
        return base_bias

    bias = base_bias.copy()

    # --- 会場タイプ分類 ---
    place_type = None
    for k, v in PLACE_GROUPS.items():
        if place in v:
            place_type = k
            break

    type_factor = {
        "イン強": 1.2,
        "センター伸び": 1.0,
        "アウト伸び": 0.5,  # ← 前回 0.6 → 0.5 に調整
        "フラット": 0.8
    }.get(place_type, 1.0)

    # =========================
    # ① 風向補正（スタンド基準）
    # =========================
    # ※ スタンドは南側固定とし、矢印方向が風向き。
    if 0 <= wind_angle < 45 or 315 <= wind_angle <= 360:
        # 向かい風（北風）→イン有利
        for i in range(1, 7):
            bias[i] += 0.12 * (4 - i) / 3 * type_factor

    elif 135 <= wind_angle <= 225:
        # 追い風（南風）→アウト有利
        for i in range(1, 7):
            bias[i] -= 0.12 * (4 - i) / 3 * type_factor

    elif 45 <= wind_angle < 135:
        # 右横風 → センター有利
        bias[3] += 0.06 * type_factor
        bias[4] += 0.06 * type_factor

    elif 225 < wind_angle < 315:
        # 左横風 → 若干不安定（全体微減）
        for i in bias:
            bias[i] -= 0.02 * type_factor

    # =========================
    # ② 風速補正
    # =========================
    if wind_speed > 7:
        # 7m以上で緩やかに上昇、上限+15%
        factor = min(1.0 + (wind_speed - 7) * 0.03, 1.15)
        for i in bias:
            # 掛け算→加算に変更（暴走防止）
            bias[i] += (factor - 1.0) * 0.5

    # =========================
    # ③ 波高補正（大波時）
    # =========================
    if wave_height >= 4:
        # 外が荒れてターン難 → 全体微減
        for i in bias:
            bias[i] -= 0.025  # 旧0.05→0.025

    # =========================
    # ④ 気温補正（低温時）
    # =========================
    if temperature <= 10:
        # モーターの回転が鈍る傾向 → 中枠がやや不利
        bias[3] -= 0.03
        bias[4] -= 0.03

    # =========================
    # ⑤ クランプ処理（安全域）
    # =========================
    for i in bias:
        bias[i] = max(min(bias[i], 1.0), -1.0)

    return bias

def _make_context_bias(place: str | None, distance_text: str | None,
                       race_type: str | None, lane: int | None = None,
                       klass: str | None = None) -> float:
    bias = 0.0

    # --- race_typeの正規化（公式の文字化け・抜け対策） ---
    if race_type:
        if "優勝" in race_type:
            race_type = "優勝戦"
        elif "準優" in race_type:
            race_type = "準優勝戦"
        elif "予選" in race_type:
            race_type = "予選"
        elif "一般" in race_type:
            race_type = "一般"
        else:
            race_type = "一般"  # fallback: 不明な文字列は一般扱い
    else:
        race_type = "一般"

    # ===== 動的場補正を取得 =====
    wind_speed = float((globals().get("CURRENT_CONTEXT", {}) or {}).get("wind_speed", 0.0))
    wind_angle = float((globals().get("CURRENT_CONTEXT", {}) or {}).get("wind_angle", 0.0))
    wave_height = float((globals().get("CURRENT_CONTEXT", {}) or {}).get("wave_height", 0.0))
    temperature = float((globals().get("CURRENT_CONTEXT", {}) or {}).get("temperature", 15.0))

    dynamic_bias = _dynamic_place_bias(place, wind_speed, wind_angle, wave_height, temperature)
    if lane in dynamic_bias:
        bias += dynamic_bias[lane] * 0.10  # ←動的バイアスは3%スケールで反映

    # 種別×級別バイアス
    if race_type and klass:
        type_bias = TYPE_BIAS.get(race_type, {}).get(klass, 0.0)
        bias += type_bias * 0.01

    # 距離補正
    dist = _distance_to_int(distance_text)
    if dist:
        if dist <= 1700:
            bias += 0.004
        elif dist >= 2000:
            bias += 0.002

    return bias

# ===== メイン処理 =====
def make_feature_table_just(entries: List[Dict[str, Any]], context: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    if not entries:
        return []

    # コンテキストをグローバル参照用に退避（動的バイアスで使用）
    globals()["CURRENT_CONTEXT"] = context or {}

    place = (context or {}).get("place")
    distance_text = (context or {}).get("distance")
    race_type = (context or {}).get("type")

    # ===== 基本特性の抽出 =====
    lanes   = [_to_float(e.get("lane"), SAFE_DEFAULTS["lane"]) for e in entries]
    st_vals = [_to_float(e.get("avg_st"), SAFE_DEFAULTS["avg_st"]) for e in entries]
    win_vals = [
        0.7 * _to_float(e.get("national_win"), SAFE_DEFAULTS["national_win"]) +
        0.3 * _to_float(e.get("local_win"), SAFE_DEFAULTS["local_win"])
        for e in entries
    ]

    def safe_val(e, key): return _to_float(e.get(key), SAFE_DEFAULTS[key], key)
    nat2, loc2 = [safe_val(e, "national_2r") for e in entries], [safe_val(e, "local_2r") for e in entries]
    mot2, bot2 = [safe_val(e, "motor_2r") for e in entries], [safe_val(e, "boat_2r") for e in entries]
    nat3, loc3 = [safe_val(e, "national_3r") for e in entries], [safe_val(e, "local_3r") for e in entries]
    mot3, bot3 = [safe_val(e, "motor_3r") for e in entries], [safe_val(e, "boat_3r") for e in entries]

    # ===== 直前展示データ =====
    exhibit_vals = [_to_float(e.get("exhibit_time"), 7.00, "exhibit_time") for e in entries]
    tilt_vals = [_to_float(e.get("tilt"), 0.0, "tilt") for e in entries]
    st_disp_vals = [_to_float(e.get("st"), 0.2, "st_display") for e in entries]
    course_vals = [_to_float(e.get("course"), e.get("lane")) for e in entries]
    adj_w_vals = [_to_float(e.get("adjust_weight"), 0.0, "adjust_weight") for e in entries]

    # ===== 正規化範囲 =====
    ln_lo, ln_hi = _safe_minmax(lanes)
    st_lo, st_hi = _safe_minmax(st_vals)
    wr_lo, wr_hi = _safe_minmax(win_vals)
    nat2_lo, nat2_hi = _safe_minmax(nat2)
    loc2_lo, loc2_hi = _safe_minmax(loc2)
    mot2_lo, mot2_hi = _safe_minmax(mot2)
    bot2_lo, bot2_hi = _safe_minmax(bot2)
    nat3_lo, nat3_hi = _safe_minmax(nat3)
    loc3_lo, loc3_hi = _safe_minmax(loc3)
    mot3_lo, mot3_hi = _safe_minmax(mot3)
    bot3_lo, bot3_hi = _safe_minmax(bot3)

    ex_lo, ex_hi = _safe_minmax(exhibit_vals)
    st_d_lo, st_d_hi = _safe_minmax(st_disp_vals)
    course_lo, course_hi = _safe_minmax(course_vals)
    tilt_lo, tilt_hi = _safe_minmax(tilt_vals)
    adj_lo, adj_hi = _safe_minmax(adj_w_vals)

    # ===== 重み設定 =====
    W = {
        "lane": 0.22,
        "st": 0.20,
        "win": 0.20,
        "two_natloc": 0.15,
        "two_mecha": 0.12,
        "three_mix": 0.11,
    }
    W_EX = {
        "exhibit_time": 0.08,
        "tilt": 0.03,
        "course": 0.04,
        "st_display": 0.06,
        "adjust_weight": 0.02,
        "weather_factor": 0.05,
    }

    # ===== 各艇スコア算出 =====
    for e in entries:
        f_lane = _norm_inverse(_to_float(e.get("lane"), SAFE_DEFAULTS["lane"]), ln_lo, ln_hi)
        f_st   = _norm_inverse(_to_float(e.get("avg_st"), SAFE_DEFAULTS["avg_st"]), st_lo, st_hi)

        w_blend = (
            0.7 * _to_float(e.get("national_win"), SAFE_DEFAULTS["national_win"]) +
            0.3 * _to_float(e.get("local_win"), SAFE_DEFAULTS["local_win"])
        )
        f_win = _norm_direct(w_blend, wr_lo, wr_hi)

        f_natloc2 = (
            0.5 * _norm_direct(safe_val(e, "national_2r"), nat2_lo, nat2_hi) +
            0.5 * _norm_direct(safe_val(e, "local_2r"),    loc2_lo, loc2_hi)
        )
        f_mecha2 = (
            0.5 * _norm_direct(safe_val(e, "motor_2r"), mot2_lo, mot2_hi) +
            0.5 * _norm_direct(safe_val(e, "boat_2r"),  bot2_lo, bot2_hi)
        )
        f_three = (
            0.25 * _norm_direct(safe_val(e, "national_3r"), nat3_lo, nat3_hi) +
            0.25 * _norm_direct(safe_val(e, "local_3r"),    loc3_lo, loc3_hi) +
            0.25 * _norm_direct(safe_val(e, "motor_3r"),    mot3_lo, mot3_hi) +
            0.25 * _norm_direct(safe_val(e, "boat_3r"),     bot3_lo, bot3_hi)
        )

        base = (
            W["lane"]      * f_lane   +
            W["st"]        * f_st     +
            W["win"]       * f_win    +
            W["two_natloc"]* f_natloc2+
            W["two_mecha"] * f_mecha2 +
            W["three_mix"] * f_three
        ) * 100.0

        # ===== 展示スコア =====
        f_ex = _norm_inverse(_to_float(e.get("exhibit_time"), 7.00), ex_lo, ex_hi)
        f_tilt = 1 - min(abs(_to_float(e.get("tilt"), 0.0)) / 1.5, 1.0)
        f_course = _norm_inverse(_to_float(e.get("course"), e.get("lane")), course_lo, course_hi)
        f_st_d = _norm_inverse(_to_float(e.get("st"), 0.2), st_d_lo, st_d_hi)
        f_adj = _norm_inverse(_to_float(e.get("adjust_weight"), 0.0), adj_lo, adj_hi)

        exhibit_score = (
            W_EX["exhibit_time"]*f_ex +
            W_EX["tilt"]*f_tilt +
            W_EX["course"]*f_course +
            W_EX["st_display"]*f_st_d +
            W_EX["adjust_weight"]*f_adj
        ) * 100.0

        base_total = base + exhibit_score

        # ===== 天候補正（8方位＋連続角度対応） =====
        wind = _to_float((context or {}).get("wind_speed"), 0.0)
        wave = _to_float((context or {}).get("wave_height"), 0.0)
        rel_wind = (context or {}).get("relative_wind")
        rel_angle = _to_float((context or {}).get("relative_angle"), 0.0)

        mult_weather = 1.0

        # --- 風速・波高の基本減衰（非線形） ---
        if wind > 6:
            mult_weather -= 0.015 * ((wind - 6) ** 1.2)
        if wave > 10:
            mult_weather -= 0.015 * ((wave - 10) / 10)

        # --- 相対風向の方向補正（8方位） ---
        if rel_wind in ("向かい風", "右向かい風", "左向かい風"):
            # 向かい系 → イン寄り有利
            mult_weather += 0.02 * (1 if e.get("course") <= 3 else -0.5)
        elif rel_wind in ("追い風", "右追い風", "左追い風"):
            # 追い系 → アウト寄り有利
            mult_weather += 0.015 * (1 if e.get("course") >= 4 else -0.5)
        elif rel_wind == "右横風":
            # 右横風 → スタンドから見て内側がやや有利
            mult_weather += 0.01 * (1 if e.get("course") <= 2 else -0.5)
        elif rel_wind == "左横風":
            # 左横風 → アウト側やや有利
            mult_weather += 0.01 * (1 if e.get("course") >= 5 else -0.5)
        elif rel_wind == "斜め風":
            # 曖昧な表現 → 角度補正で判定
            if 150 <= rel_angle <= 210:
                mult_weather += 0.01 * (1 if e.get("course") <= 3 else -0.5)
            elif 330 <= rel_angle or rel_angle <= 30:
                mult_weather += 0.01 * (1 if e.get("course") >= 4 else -0.5)

        # --- 角度の連続補正（真正向かい・真正追いを強調） ---
        if 150 <= rel_angle <= 210:  # 真向かい
            mult_weather += 0.01 * (1 if e.get("course") <= 3 else -0.3)
        elif 330 <= rel_angle or rel_angle <= 30:  # 真追い
            mult_weather += 0.008 * (1 if e.get("course") >= 4 else -0.3)

        # --- 強風＋高波時の複合ペナルティ ---
        if wind > 6 and wave >= 4:
            mult_weather -= 0.01 * ((wind - 6) * (wave / 4))

        # --- 安全範囲クランプ ---
        mult_weather = max(min(mult_weather, 1.25), 0.75)

        # ===== コンテキスト補正 =====
        mult_context = 1.0 + _make_context_bias(place, distance_text, race_type,
                                                e.get("lane"), e.get("klass"))

        final = round(base_total * mult_context * mult_weather, 1)

        # ===== 出力 =====
        e["score_breakdown"] = {
            "lane": round(W["lane"] * f_lane * 100, 1),
            "st": round(W["st"] * f_st * 100, 1),
            "win": round(W["win"] * f_win * 100, 1),
            "two_natloc": round(W["two_natloc"] * f_natloc2 * 100, 1),
            "two_mecha": round(W["two_mecha"] * f_mecha2 * 100, 1),
            "three_mix": round(W["three_mix"] * f_three * 100, 1),
            "exhibit": round(exhibit_score, 1),
            "context_mult": round(mult_context, 4),
            "weather_mult": round(mult_weather, 4),
            "base": round(base_total, 1),
        }
        e["score"] = final


        # 風速が弱い時の静水補正（例：内枠信頼度をわずかに上げる）
        ctx = globals().get("CURRENT_CONTEXT", {}) or {}
        wind_speed = float(ctx.get("wind_speed", 0.0))
        if wind_speed < 3:
            lane = int(e.get("lane", 3))
            e["score"] *= 1.0 + (0.03 * (4 - lane) / 3)

    entries.sort(key=lambda x: _to_float(x.get("lane"), SAFE_DEFAULTS["lane"]))
    return entries