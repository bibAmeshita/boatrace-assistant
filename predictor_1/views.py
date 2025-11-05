# predictor_1/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json, os
from datetime import datetime

from predictor_1.features import make_feature_table

@csrf_exempt
def race_predict(request):
    body = json.loads(request.body)

    data = body  # 入力そのまま

    # entries + context
    entries = data.get("entries", [])
    context = {
        "place": data.get("place"),
        "distance": data.get("distance"),
        "type": data.get("type"),
    }

    # score 付与
    new_entries = make_feature_table(entries, context)
    data["entries"] = new_entries

    # ✅ 新：買い目生成
    from predictor_1.rules import make_trifecta_1axle
    kaime = make_trifecta_1axle(new_entries, int(data.get("points", 5)))
    data["tickets"] = kaime

    # ===== ✅ 完成版JSON保存 =====
    save_dir = "data/predicted"
    os.makedirs(save_dir, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    race_no = data.get("race", "unknown")

    filename = f"{save_dir}/predicted_{today}_{race_no}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 完成版保存: {filename}")

    print(json.dumps(data, ensure_ascii=False, indent=2))
    # フロントに返す
    return JsonResponse(data, json_dumps_params={"ensure_ascii": False})