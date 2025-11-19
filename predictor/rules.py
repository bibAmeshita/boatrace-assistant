# predictor_1/rules.py
from typing import List, Dict, Any
import itertools


#3連単・通常買い
def make_trifecta_normal(entries, points):
    """
    3連単 通常買い（スコア順に基づいて上位艇の組み合わせを生成）
    """
    from itertools import permutations

    if not entries or len(entries) < 3:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    # スコア順で並び替え
    sorted_entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)

    # 上位6艇までを対象
    lanes = [e["lane"] for e in sorted_entries[:6]]

    # 上位艇から3連単順列を生成
    combos = list(permutations(lanes, 3))

    # スコア合計の高い順にソート
    entry_scores = {e["lane"]: e["score"] for e in sorted_entries}
    combos.sort(
        key=lambda t: entry_scores[t[0]] + entry_scores[t[1]] + entry_scores[t[2]],
        reverse=True
    )

    # 上位points件を選択
    selected = [f"{a}-{b}-{c}" for a, b, c in combos[:points]]

    return {
        "tickets": selected,
        "formation": "通常",
        "count": len(selected),
        "note": f"指数順 3連単 通常 {len(selected)}点"
    }

# 3連単・1軸流し
def make_trifecta_1axle(entries: List[Dict[str, Any]], points: int) -> Dict[str, Any]:
    """
    3連単・1軸流し（points = 買い目数）
    軸 → スコア最大
    相手 → 次点スコア順
    組合せ数がpointsを超える場合、スコア順でpoints点まで制限
    """

    if not entries or len(entries) < 3:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    # スコア順（降順）
    sorted_entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)

    # 軸艇（スコア最大）
    axis = sorted_entries[0]["lane"]

    # 相手候補（軸以外）
    rivals = [e["lane"] for e in sorted_entries[1:]]

    # すべての相手2連順列を作成（同一禁止）
    combos = [f"{axis}-{r2}-{r3}" for r2, r3 in itertools.permutations(rivals, 2)]

    # スコア順（r2, r3の合計スコアが高い順）で並べ替え
    entry_scores = {e["lane"]: e["score"] for e in sorted_entries}
    combos = sorted(
        combos,
        key=lambda t: entry_scores[int(t.split('-')[1])] + entry_scores[int(t.split('-')[2])],
        reverse=True
    )

    # 上位points点だけ残す
    selected = combos[:points]

    formation = f"{axis}-({' '.join(map(str, rivals))})"

    return {
        "tickets": selected,
        "formation": formation,
        "count": len(selected),
        "note": f"指数順 3連単1軸流し / {points}点出力"
    }

# 3連単・2軸流し
def make_trifecta_2axle(entries, points):
    """
    3連単・2軸流し（points = 相手の数）
    - スコア上位2艇を軸に固定
    - 残りから相手艇を points 件選ぶ
    - 軸2艇の順序を考慮（A→B、B→A）
    - 相手は軸艇と重複しない
    """

    if not entries or len(entries) < 3:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    # スコア順（降順）
    sorted_entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)

    # 軸艇（上位2）
    axis1 = sorted_entries[0]["lane"]
    axis2 = sorted_entries[1]["lane"]

    # 相手候補（残り）
    rivals = [e["lane"] for e in sorted_entries[2:]]
    rivals = rivals[:points]  # 指定数だけ

    entry_scores = {e["lane"]: e["score"] for e in sorted_entries}
    combos = []
    # 軸1→軸2 と 軸2→軸1 の両方で生成
    for r in rivals:
        combos.append((axis1, axis2, r))
        combos.append((axis2, axis1, r))

    # スコア合計の高い順にソート
    combos.sort(
        key=lambda t: entry_scores[t[0]] + entry_scores[t[1]] + entry_scores[t[2]],
        reverse=True
    )

    # 上位points件まで（両方向含めるため points×2 の上限もあり）
    selected = [f"{a}-{b}-{c}" for a, b, c in combos[:points * 2]]

    formation = f"({axis1}{axis2})→({''.join(map(str, rivals))})"

    return {
        "tickets": selected,
        "formation": formation,
        "count": len(selected),
        "note": f"指数順 3連単2軸流し / 相手{points}点（計{len(selected)}点）"
    }

# 3連単・3艇ボックス
def make_trifecta_3box(entries, _points=None):
    """
    3連単・3艇ボックス
    上位3艇から全組み合わせ（順序あり）
    → 3P3 = 6点固定
    """
    if len(entries) < 3:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    top = sorted(entries, key=lambda e: e["score"], reverse=True)[:3]
    lanes = [e["lane"] for e in top]
    tickets = [f"{a}-{b}-{c}" for a, b, c in itertools.permutations(lanes, 3)]

    return {
        "tickets": tickets,
        "formation": f"BOX({''.join(map(str, lanes))})",
        "count": len(tickets),
        "note": "指数順 3連単3艇ボックス（6点）"
    }

# 3連単・4艇ボックス
def make_trifecta_4box(entries, _points=None):
    """
    3連単・4艇ボックス
    上位4艇から全組み合わせ（順序あり）
    → 4P3 = 24点固定
    """
    if len(entries) < 4:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    top = sorted(entries, key=lambda e: e["score"], reverse=True)[:4]
    lanes = [e["lane"] for e in top]
    tickets = [f"{a}-{b}-{c}" for a, b, c in itertools.permutations(lanes, 3)]

    return {
        "tickets": tickets,
        "formation": f"BOX({''.join(map(str, lanes))})",
        "count": len(tickets),
        "note": "指数順 3連単4艇ボックス（24点）"
    }

# 3連単・5艇ボックス
def make_trifecta_5box(entries, _points=None):
    """
    3連単・5艇ボックス
    上位5艇から全組み合わせ（順序あり）
    → 5P3 = 60点固定
    """
    if len(entries) < 5:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    top = sorted(entries, key=lambda e: e["score"], reverse=True)[:5]
    lanes = [e["lane"] for e in top]
    tickets = [f"{a}-{b}-{c}" for a, b, c in itertools.permutations(lanes, 3)]

    return {
        "tickets": tickets,
        "formation": f"BOX({''.join(map(str, lanes))})",
        "count": len(tickets),
        "note": "指数順 3連単5艇ボックス（60点）"
    }

# 3連複 通常
def make_trio_normal(entries, points=3):
    """
    3連複 通常：スコア上位から順不同で3艇選出
    例: [(1,2,3)]
    """

    from itertools import combinations
    # スコア順に並べて上位5艇を対象に
    sorted_entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)
    lanes = [e["lane"] for e in sorted_entries[:5]]

    # 3艇順不同の全組合せ
    combos = list(combinations(lanes, 3))

    # スコア合計順で並べ替え
    entry_scores = {e["lane"]: e["score"] for e in sorted_entries}
    combos.sort(
        key=lambda t: entry_scores[t[0]] + entry_scores[t[1]] + entry_scores[t[2]],
        reverse=True
    )

    # 上位points件を選択
    selected = [tuple(sorted(c)) for c in combos[:points]]
    return {
        "tickets": [f"{a}-{b}-{c}" for a, b, c in selected],
        "formation": "通常",
        "count": len(selected),
        "note": f"指数順 3連複 通常 / {len(selected)}点"
    }


# 3連複 1軸流し
def make_trio_1axle(entries, points=5):
    """
    3連複 1軸流し：軸1艇 + 相手(points)艇の順不同組合せ
    例: 軸1 + 相手3艇 → 3C2 = 3点
    """
    lanes = [e["lane"] for e in sorted(entries, key=lambda x: x["score"], reverse=True)]
    axis = lanes[0]
    others = lanes[1 : 1 + points]
    return [tuple(sorted((axis, a, b))) for a, b in combinations(others, 2)]

#3連複 2軸流し
def make_trio_2axle(entries, points=4):
    """
    3連複 2軸流し：軸2艇 + 相手(points)艇の順不同組合せ
    例: 軸(1,2) + 相手3艇 → 3点
    """
    lanes = [e["lane"] for e in sorted(entries, key=lambda x: x["score"], reverse=True)]
    axis1, axis2 = lanes[:2]
    others = lanes[2 : 2 + points]
    return [tuple(sorted((axis1, axis2, o))) for o in others]

#3連複 ボックス
def make_trio_box(entries, points=3):
    """
    3連複 ボックス：points艇の全順不同組合せ
    例: 3艇 → 1点, 4艇 → 4点, 5艇 → 10点
    """
    lanes = [e["lane"] for e in sorted(entries, key=lambda x: x["score"], reverse=True)]
    selected = lanes[:points]
    return [tuple(sorted(c)) for c in combinations(selected, 3)]

# 2連単・通常
def make_exacta(entries: List[Dict[str, Any]], points: int) -> Dict[str, Any]:
    """
    2連単（順番あり）
    - スコア上位艇をもとに上位N点の組み合わせを生成
    """
    if not entries or len(entries) < 2:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    # スコア順（降順）
    sorted_entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)

    # 順列（2艇）
    combos = []
    for i in range(len(sorted_entries)):
        for j in range(len(sorted_entries)):
            if i != j:
                t = f"{sorted_entries[i]['lane']}-{sorted_entries[j]['lane']}"
                combos.append({
                    "pair": t,
                    "score_sum": sorted_entries[i]["score"] + sorted_entries[j]["score"],
                })

    # スコア合算の上位points件
    combos.sort(key=lambda c: c["score_sum"], reverse=True)
    selected = combos[:points]

    tickets = [c["pair"] for c in selected]
    formation = " / ".join(tickets)

    return {
        "tickets": tickets,
        "formation": formation,
        "count": len(tickets),
        "note": f"指数順 2連単 / 上位{points}点"
    }

# 2連単・1軸流し
def make_exacta_1axle(entries, points: int):
    """
    2連単・1軸流し（順序あり）
    - 軸：スコア最大
    - 相手：上位から points艇
    - 組合せ：軸→相手 の順序固定
    """
    if not entries or len(entries) < 2:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    # スコア順
    sorted_entries = sorted(entries, key=lambda e: e["score"], reverse=True)
    axis = sorted_entries[0]["lane"]
    rivals = [e["lane"] for e in sorted_entries[1:points+1]]

    tickets = [f"{axis}-{r}" for r in rivals]

    return {
        "tickets": tickets,
        "formation": f"{axis}-({' '.join(map(str, rivals))})",
        "count": len(tickets),
        "note": f"指数順 2連単1軸流し / 相手{points}艇"
    }

# 2連単・BOX
def make_exacta_box(entries, _points=None):
    """
    2連単・BOX
    上位艇から全順序あり組み合わせ
    例）4艇BOXなら 4P2 = 12点
    """
    if len(entries) < 2:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    top = sorted(entries, key=lambda e: e["score"], reverse=True)
    lanes = [e["lane"] for e in top[:_points or len(entries)]]
    tickets = [f"{a}-{b}" for a, b in itertools.permutations(lanes, 2)]

    return {
        "tickets": tickets,
        "formation": f"BOX({''.join(map(str, lanes))})",
        "count": len(tickets),
        "note": f"指数順 2連単BOX（{len(tickets)}点）"
    }

# 2連複・通常
def make_quinella(entries: List[Dict[str, Any]], points: int) -> Dict[str, Any]:
    """
    2連複（順番なし）
    - スコア上位艇から、順不同ペアを生成
    """
    if not entries or len(entries) < 2:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    sorted_entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)

    combos = []
    for i in range(len(sorted_entries)):
        for j in range(i + 1, len(sorted_entries)):
            t = f"{sorted_entries[i]['lane']}-{sorted_entries[j]['lane']}"
            combos.append({
                "pair": t,
                "score_sum": sorted_entries[i]["score"] + sorted_entries[j]["score"],
            })

    combos.sort(key=lambda c: c["score_sum"], reverse=True)
    selected = combos[:points]

    tickets = [c["pair"] for c in selected]
    formation = " / ".join(tickets)

    return {
        "tickets": tickets,
        "formation": formation,
        "count": len(tickets),
        "note": f"指数順 2連複 / 上位{points}点"
    }

# 連複・1軸流し
def make_quinella_1axle(entries, points: int):
    """
    2連複・1軸流し（順序なし）
    - 軸：スコア最大
    - 相手：上位から points艇
    - 組合せ：軸−相手（順不同）
    """
    if not entries or len(entries) < 2:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    # スコア順
    sorted_entries = sorted(entries, key=lambda e: e["score"], reverse=True)
    axis = sorted_entries[0]["lane"]
    rivals = [e["lane"] for e in sorted_entries[1:points+1]]

    tickets = [f"{min(axis, r)}-{max(axis, r)}" for r in rivals]

    return {
        "tickets": tickets,
        "formation": f"{axis}-({' '.join(map(str, rivals))})",
        "count": len(tickets),
        "note": f"指数順 2連複1軸流し / 相手{points}艇"
    }

# 2連複・BOX
def make_quinella_box(entries, _points=None):
    """
    2連複・BOX
    上位艇から全順不同組み合わせ
    例）4艇BOXなら 4C2 = 6点
    """
    if len(entries) < 2:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    top = sorted(entries, key=lambda e: e["score"], reverse=True)
    lanes = [e["lane"] for e in top[:_points or len(entries)]]
    tickets = [f"{min(a,b)}-{max(a,b)}" for a, b in itertools.combinations(lanes, 2)]

    return {
        "tickets": tickets,
        "formation": f"BOX({''.join(map(str, lanes))})",
        "count": len(tickets),
        "note": f"指数順 2連複BOX（{len(tickets)}点）"
    }

# 単勝
def make_win(entries: List[Dict[str, Any]], points: int) -> Dict[str, Any]:
    """
    単勝：指数順に上位N艇を選ぶ
    """
    if not entries:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    sorted_entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)

    points = max(1, min(int(points or 1), len(sorted_entries)))

    selected = [str(e["lane"]) for e in sorted_entries[:points]]

    return {
        "tickets": selected,
        "formation": " / ".join(selected),
        "count": len(selected),
        "note": f"指数順 単勝 / 上位{points}艇"
    }

# 複勝
def make_place(entries: List[Dict[str, Any]], points: int) -> Dict[str, Any]:
    """
    複勝：指数順に上位N艇を選ぶ（3着以内想定）
    """
    if not entries:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    sorted_entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)

    points = max(1, min(int(points or 1), len(sorted_entries)))

    selected = [str(e["lane"]) for e in sorted_entries[:points]]

    return {
        "tickets": selected,
        "formation": " / ".join(selected),
        "count": len(selected),
        "note": f"指数順 複勝 / 上位{points}艇（3着以内想定）"
    }

# 3連単・ボックス汎用ラッパー
def make_trifecta_box(entries, points=None):
    """
    3連単・ボックス（統一呼び出し用）
    - points数に応じて 3艇 / 4艇 / 5艇 ボックスを自動選択
    """
    if not entries or len(entries) < 3:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    from itertools import permutations

    # スコア順で上位艇を抽出（pointsが小さい場合でも柔軟に対応）
    sorted_entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)
    lanes = [e["lane"] for e in sorted_entries[: min(6, len(sorted_entries))]]

    # 3連単全組合せ
    combos = list(permutations(lanes, 3))

    # スコア合計順で並べ替え
    entry_scores = {e["lane"]: e["score"] for e in sorted_entries}
    combos.sort(
        key=lambda t: entry_scores[t[0]] + entry_scores[t[1]] + entry_scores[t[2]],
        reverse=True
    )

    # 上位points件に制限（未指定時は全件）
    limit = len(combos) if not points or points <= 0 else points
    selected = [f"{a}-{b}-{c}" for a, b, c in combos[:limit]]

    return {
        "tickets": selected,
        "formation": f"BOX({' '.join(map(str, lanes))})",
        "count": len(selected),
        "note": f"指数順 3連単BOX / {len(selected)}点"
    }