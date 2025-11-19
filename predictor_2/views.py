# predictor_2/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json, os, re
from datetime import datetime

from predictor_2.features import make_feature_table_just
from predictor_2 import rules

from predictor_2.prompts import build_ai_prompt
from predictor_2.ai_client import call_ai

@csrf_exempt
def race_predict(request):
    try:
        body = json.loads(request.body)
        result = run_race_predict_logic(body)
        return JsonResponse(result, json_dumps_params={"ensure_ascii": False})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def run_race_predict_logic(data):

    try:
        print("💥買い目つける開始")
        # entries + context
        entries = data.get("entries", [])
        context = {
            "place": data.get("place"),
            "distance": data.get("distance"),
            "type": data.get("type"),
        }

        # スコア付与
        new_entries = make_feature_table_just(entries, context)
        data["entries"] = new_entries

        bet_type = data.get("betType", "")
        method = data.get("method", "")
        points = int(data.get("points", 5))

        # デフォルト
        kaime = {"tickets": [], "formation": "", "count": 0, "note": "未対応方式"}

        # キー： (式別, 方式)
        func_map = {
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

        func = func_map.get((bet_type, method))
        if not func:
            data["error"] = f"未対応方式: {bet_type} {method}"
            return data  # ← JsonResponse は返さない

        # 予想作成
        kaime = func(new_entries, points)
        data["tickets"] = kaime

        # ===== 保存 =====
        save_dir = "data"
        os.makedirs(save_dir, exist_ok=True)

        place = data.get("place", "unknown")
        race_no = data.get("race", "unknown")
        today = datetime.now().strftime("%Y%m%d")

        filename = f"{save_dir}/race_detail_{place}_{today}_{race_no}.json"

        if os.path.exists(filename):
            os.remove(filename)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


        # ===== AI =====
        print("💥AIコメントつける開始")

        prompt = build_ai_prompt(data)
        raw_ai_response = call_ai(prompt)

        try:
            parsed_ai = clean_ai_json(raw_ai_response)
            data["ai"] = parsed_ai["ai"]
        except Exception as e:
            print("AI JSON パース失敗:", e)
            data["ai"] = {
                "error": "AI JSON parse failed",
                "raw": raw_ai_response
            }

        return data

    except Exception as e:
        import traceback
        print("🚨 run_race_predict_logic 例外:", e)
        traceback.print_exc()
        # 内部処理なので JsonResponse を返さない
        return {"error": str(e)}

def clean_ai_json(ai_raw: str):
    # コードブロックの除去
    cleaned = re.sub(r"```json|```", "", ai_raw).strip()
    # JSON読み込み
    return json.loads(cleaned)