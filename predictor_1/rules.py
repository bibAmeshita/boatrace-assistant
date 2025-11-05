# predictor_1/rules.py
from typing import List, Dict, Any

def make_trifecta_1axle(entries: List[Dict[str, Any]], points: int) -> Dict[str, Any]:
    """
    3連単・1軸流し（points = 買い目数）
    - スコア順で1艇軸
    - 残りからスコア順に相手選択
    - 軸 → 1番人気（score最大）
    - 相手 → 次点スコア順
    """

    if not entries or len(entries) < 3:
        return {"tickets": [], "formation": "", "count": 0, "note": "error: entries不足"}

    # スコア順（降順）
    sorted_entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)

    # 軸艇
    axis = sorted_entries[0]["lane"]

    # 相手（軸以外）
    rivals = [e["lane"] for e in sorted_entries[1:]]

    # 上位の相手を points だけ
    rivals = rivals[:points]

    # フォーメーション形成
    tickets = []
    for r2 in rivals:
        for r3 in rivals:
            if r2 != r3:  # 同一艇番号禁止
                tickets.append(f"{axis}-{r2}-{r3}")

    formation = f"{axis}-({''.join(map(str, rivals))})-({''.join(map(str, rivals))})"

    return {
        "tickets": tickets,
        "formation": formation,
        "count": len(tickets),
        "note": f"指数順 3連単1軸流し / {points}点想定"
    }