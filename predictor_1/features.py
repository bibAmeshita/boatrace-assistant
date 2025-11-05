# predictor_1/features.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple
import re

Number = float

# 欠損時の安全デフォルト値（entriesのキーに合わせて定義）
SAFE_DEFAULTS = {
    "lane": 9,                # 1が有利。小さいほど良いのであとで逆正規化
    "avg_st": 0.18,           # スタート平均。小さいほど良い
    "national_win": 4.50,     # 勝率（全国）
    "local_win": 4.50,        # 勝率（当地）
    "national_2r": 30.0,      # 2連対率（全国）
    "local_2r": 30.0,         # 2連対率（当地）
    "motor_2r": 30.0,         # 2連対率（モーター）
    "boat_2r": 30.0,          # 2連対率（ボート）
    "national_3r": 45.0,      # 3連対率（全国）
    "local_3r": 45.0,         # 3連対率（当地）
    "motor_3r": 45.0,         # 3連対率（モーター）
    "boat_3r": 45.0,          # 3連対率（ボート）
    "weight": 52.0,
}

# 場・種別の簡易補正（あとで運用しながらチューニング前提）
PLACE_BIAS = {
    # 北関東〜関東
    "桐生": 0.010,
    "戸田": 0.015,      # 狭水面、事故多め
    "江戸川": 0.030,    # 超荒水面、風の魔境
    "平和島": 0.020,    # 海風で荒れる
    "多摩川": -0.005,   # イン強め、淡水
    "千葉": 0.000,      # ※開催終了（補欠用）

    # 東海
    "浜名湖": 0.005,    # 風強め
    "蒲郡": -0.005,     # イン強め
    "常滑": 0.005,

    # 近畿
    "津": -0.005,
    "三国": -0.010,     # イン堅い
    "びわこ": 0.010,
    "尼崎": -0.005,
    "住之江": -0.010,   # 都会のイン王国

    # 中国・四国
    "鳴門": 0.005,
    "丸亀": -0.005,
    "児島": -0.005,
    "宮島": 0.010,
    "徳山": -0.020,     # 全国トップクラスのイン水面

    # 九州
    "下関": -0.010,
    "若松": -0.010,
    "芦屋": -0.015,     # 全体的に堅い
    "福岡": 0.010,      # 荒れる日多い
    "唐津": 0.005
}
TYPE_BIAS = {
    # 「格が上がるほど実力通りになりやすい」想定の微補正
    "一般": 0.000,
    "予選": 0.003,
    "準優勝戦": 0.010,
    "優勝戦": 0.015,
}

def _to_float(v: Any, default: Number) -> Number:
    try:
        if v in (None, "", "-", "--"):
            return default
        if isinstance(v, str):
            return float(v.replace("%", "").strip())
        return float(v)
    except Exception:
        return default

def _safe_minmax(vals: List[Number]) -> Tuple[Number, Number]:
    clean = [v for v in vals if isinstance(v, (int, float))]
    if not clean:
        return 0.0, 1.0
    lo, hi = min(clean), max(clean)
    if lo == hi:
        # 全部同じ値ならレンジを作る（ゼロ割回避＆一律0.5にならないように）
        hi = lo + (abs(lo) if lo != 0 else 1.0)
    return lo, hi

def _norm_direct(x: Number, lo: Number, hi: Number) -> Number:
    # 大きいほど良い指標（例: 勝率、連対率）
    return (x - lo) / (hi - lo) if hi != lo else 0.5

def _norm_inverse(x: Number, lo: Number, hi: Number) -> Number:
    # 小さいほど良い指標（例: 枠番、平均ST）
    return (hi - x) / (hi - lo) if hi != lo else 0.5

def _distance_to_int(distance_text: str | None) -> int | None:
    if not distance_text:
        return None
    m = re.search(r"(\d+)", str(distance_text))
    return int(m.group(1)) if m else None

def _make_context_bias(place: str | None, distance_text: str | None, race_type: str | None) -> float:
    """
    場・距離・種別の素朴な加点（乗算係数用の微小値）
    例）+0.01 なら最終スコアに (1 + 0.01) を掛けるイメージ
    """
    bias = 0.0

    # 場補正（辞書にあれば加点）
    if place:
        bias += PLACE_BIAS.get(place, 0.0)

    # 種別補正（辞書にあれば加点）
    if race_type:
        bias += TYPE_BIAS.get(race_type, 0.0)

    # 距離補正（簡易：超短距離/超長距離で内枠有利が増す傾向…を全体にわずかに反映）
    dist = _distance_to_int(distance_text)
    if dist:
        if dist <= 1700:
            bias += 0.004
        elif dist >= 2000:
            bias += 0.002
        # 中距離は 0

    return bias

def make_feature_table(
    entries: List[Dict[str, Any]],
    context: Dict[str, Any] | None = None
) -> List[Dict[str, Any]]:
    """
    entries: today_race_detail が返した entries（6艇分）
    context: { "place": str, "distance": "1800m", "type": "予選", ... } の想定（任意）

    返却：各エントリに score と内訳を付けて lane 昇順で返す
    """
    if not entries:
        return []

    place = (context or {}).get("place")
    distance_text = (context or {}).get("distance")
    race_type = (context or {}).get("type")

    # ===== 値を抽出（安全に数字化）=====
    lanes   = [_to_float(e.get("lane"),        SAFE_DEFAULTS["lane"])        for e in entries]
    st_vals = [_to_float(e.get("avg_st"),      SAFE_DEFAULTS["avg_st"])      for e in entries]

    # 勝率は全国＋当地のブレンド（全国をやや重視）
    win_vals = [
        0.7 * _to_float(e.get("national_win"), SAFE_DEFAULTS["national_win"])
      + 0.3 * _to_float(e.get("local_win"),    SAFE_DEFAULTS["local_win"])
        for e in entries
    ]

    # 2連：全国/当地 + モーター/ボート をブレンド
    nat2 = [_to_float(e.get("national_2r"), SAFE_DEFAULTS["national_2r"]) for e in entries]
    loc2 = [_to_float(e.get("local_2r"),    SAFE_DEFAULTS["local_2r"])    for e in entries]
    mot2 = [_to_float(e.get("motor_2r"),    SAFE_DEFAULTS["motor_2r"])    for e in entries]
    bot2 = [_to_float(e.get("boat_2r"),     SAFE_DEFAULTS["boat_2r"])     for e in entries]

    # 3連：全国/当地 + モーター/ボート
    nat3 = [_to_float(e.get("national_3r"), SAFE_DEFAULTS["national_3r"]) for e in entries]
    loc3 = [_to_float(e.get("local_3r"),    SAFE_DEFAULTS["local_3r"])    for e in entries]
    mot3 = [_to_float(e.get("motor_3r"),    SAFE_DEFAULTS["motor_3r"])    for e in entries]
    bot3 = [_to_float(e.get("boat_3r"),     SAFE_DEFAULTS["boat_3r"])     for e in entries]

    # ===== min/max（正規化レンジ）=====
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

    # ===== ウェイト（後でチューニングしやすいようまとめる）=====
    W = {
        "lane": 0.22,      # 枠
        "st": 0.20,        # スタート
        "win": 0.20,       # 勝率ブレンド
        "two_natloc": 0.15,# 2連（全国/当地）
        "two_mecha": 0.12, # 2連（モーター/ボート）
        "three_mix": 0.11, # 3連（総合）
    }
    # 合計 = 1.00

    # ===== スコア算出 =====
    for e in entries:
        # 逆/順の正規化
        f_lane = _norm_inverse(_to_float(e.get("lane"),   SAFE_DEFAULTS["lane"]),   ln_lo, ln_hi)
        f_st   = _norm_inverse(_to_float(e.get("avg_st"), SAFE_DEFAULTS["avg_st"]), st_lo, st_hi)

        w_blend = (
            0.7 * _to_float(e.get("national_win"), SAFE_DEFAULTS["national_win"]) +
            0.3 * _to_float(e.get("local_win"),    SAFE_DEFAULTS["local_win"])
        )
        f_win = _norm_direct(w_blend, wr_lo, wr_hi)

        # 2連複系
        f_natloc2 = (
            0.5 * _norm_direct(_to_float(e.get("national_2r"), SAFE_DEFAULTS["national_2r"]), nat2_lo, nat2_hi) +
            0.5 * _norm_direct(_to_float(e.get("local_2r"),    SAFE_DEFAULTS["local_2r"]),    loc2_lo, loc2_hi)
        )
        f_mecha2 = (
            0.5 * _norm_direct(_to_float(e.get("motor_2r"), SAFE_DEFAULTS["motor_2r"]), mot2_lo, mot2_hi) +
            0.5 * _norm_direct(_to_float(e.get("boat_2r"),  SAFE_DEFAULTS["boat_2r"]),  bot2_lo, bot2_hi)
        )

        # 3連系（2連よりは弱めに効かせるが無視はしない）
        f_three = (
            0.25 * _norm_direct(_to_float(e.get("national_3r"), SAFE_DEFAULTS["national_3r"]), nat3_lo, nat3_hi) +
            0.25 * _norm_direct(_to_float(e.get("local_3r"),    SAFE_DEFAULTS["local_3r"]),    loc3_lo, loc3_hi) +
            0.25 * _norm_direct(_to_float(e.get("motor_3r"),    SAFE_DEFAULTS["motor_3r"]),    mot3_lo, mot3_hi) +
            0.25 * _norm_direct(_to_float(e.get("boat_3r"),     SAFE_DEFAULTS["boat_3r"]),     bot3_lo, bot3_hi)
        )

        # ベーススコア（0〜100）
        base = (
            W["lane"]      * f_lane   +
            W["st"]        * f_st     +
            W["win"]       * f_win    +
            W["two_natloc"]* f_natloc2+
            W["two_mecha"] * f_mecha2 +
            W["three_mix"] * f_three
        ) * 100.0

        # 場・距離・種別の小さな乗算補正
        mult = 1.0 + _make_context_bias(place, distance_text, race_type)

        final = round(base * mult, 1)

        # 参考：内訳も一緒に返しておくと検証が楽
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

    # 枠番でソート（laneは int 前提）
    entries.sort(key=lambda x: _to_float(x.get("lane"), SAFE_DEFAULTS["lane"]))
    return entries