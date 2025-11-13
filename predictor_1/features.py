# predictor_1/features.py
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
PLACE_BIAS: Dict[str, Dict[int, float]] = {
    "多摩川": {1: +1.0, 2: +0.5, 3: +0.2, 4: -0.2, 5: -0.5, 6: -0.8},
    "戸田":   {1: -0.3, 2: -0.2, 3: +0.1, 4: +0.4, 5: +0.6, 6: +0.8},
    "江戸川": {1: -0.5, 2: -0.2, 3: +0.2, 4: +0.4, 5: +0.6, 6: +0.8},
    "鳴門":   {1: +0.5, 2: +0.2, 3: 0.0, 4: -0.2, 5: -0.4, 6: -0.6},
    "徳山":   {1: +1.0, 2: +0.6, 3: +0.3, 4: -0.2, 5: -0.6, 6: -1.0},
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

    # 枠別・場バイアス
    if place and lane:
        lane_bias = PLACE_BIAS.get(place, {}).get(lane, 0.0)
        bias += lane_bias * 0.01

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
def make_feature_table(entries: List[Dict[str, Any]], context: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    if not entries:
        return []

    place = (context or {}).get("place")
    distance_text = (context or {}).get("distance")
    race_type = (context or {}).get("type")

    lanes   = [_to_float(e.get("lane"), SAFE_DEFAULTS["lane"]) for e in entries]
    st_vals = [_to_float(e.get("avg_st"), SAFE_DEFAULTS["avg_st"]) for e in entries]
    win_vals = [
        0.7 * _to_float(e.get("national_win"), SAFE_DEFAULTS["national_win"]) +
        0.3 * _to_float(e.get("local_win"), SAFE_DEFAULTS["local_win"])
        for e in entries
    ]

    # 2連・3連（0.00補正対応）
    def safe_val(e, key): return _to_float(e.get(key), SAFE_DEFAULTS[key], key)
    nat2, loc2 = [safe_val(e, "national_2r") for e in entries], [safe_val(e, "local_2r") for e in entries]
    mot2, bot2 = [safe_val(e, "motor_2r") for e in entries], [safe_val(e, "boat_2r") for e in entries]
    nat3, loc3 = [safe_val(e, "national_3r") for e in entries], [safe_val(e, "local_3r") for e in entries]
    mot3, bot3 = [safe_val(e, "motor_3r") for e in entries], [safe_val(e, "boat_3r") for e in entries]

    # 正規化
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

    W = {
        "lane": 0.22,
        "st": 0.20,
        "win": 0.20,
        "two_natloc": 0.15,
        "two_mecha": 0.12,
        "three_mix": 0.11,
    }

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

        mult = 1.0 + _make_context_bias(place, distance_text, race_type,
                                        e.get("lane"), e.get("klass"))
        final = round(base * mult, 1)

        e["score_breakdown"] = {
            "lane": round(W["lane"] * f_lane * 100, 1),
            "st": round(W["st"] * f_st * 100, 1),
            "win": round(W["win"] * f_win * 100, 1),
            "two_natloc": round(W["two_natloc"] * f_natloc2 * 100, 1),
            "two_mecha": round(W["two_mecha"] * f_mecha2 * 100, 1),
            "three_mix": round(W["three_mix"] * f_three * 100, 1),
            "context_mult": round(mult, 4),
            "base": round(base, 1),
        }
        e["score"] = final

    entries.sort(key=lambda x: _to_float(x.get("lane"), SAFE_DEFAULTS["lane"]))
    return entries