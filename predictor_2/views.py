# predictor_2/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json, os
from datetime import datetime

from predictor_2.features import make_feature_table_just
from predictor_2 import rules


@csrf_exempt
def race_predict(request):
    try:
        body = json.loads(request.body)
        data = body

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

        # ======================================
        # 🎯 式別と方式による自動切り替え
        # ======================================
        bet_type = data.get("betType", "")
        method = data.get("method", "")
        points = int(data.get("points", 5))

        # デフォルト
        kaime = {"tickets": [], "formation": "", "count": 0, "note": "未対応方式"}

        # キー： (式別, 方式)
        func_map = {
            # --- 三連単 ---
            ("3連単", "通常"): rules.make_trifecta_normal,
            ("3連単", "1軸流し"): rules.make_trifecta_1axle,
            ("3連単", "2軸流し"): rules.make_trifecta_2axle,
            ("3連単", "3艇ボックス"): rules.make_trifecta_box,
            ("3連単", "4艇ボックス"): rules.make_trifecta_box,
            ("3連単", "5艇ボックス"): rules.make_trifecta_box,

            # --- 二連単 ---
            ("2連単", "1軸流し"): rules.make_exacta_1axle,
            ("2連単", "ボックス"): rules.make_exacta_box,

            # --- 二連複 ---
            ("2連複", "1軸流し"): rules.make_quinella_1axle,
            ("2連複", "ボックス"): rules.make_quinella_box,

            # --- 三連複 ---
            ("3連複", "通常"): rules.make_trio_normal,
            ("3連複", "1軸流し"): rules.make_trio_1axle,
            ("3連複", "2軸流し"): rules.make_trio_2axle,
            ("3連複", "3艇ボックス"): rules.make_trio_box,
            ("3連複", "4艇ボックス"): rules.make_trio_box,
            ("3連複", "5艇ボックス"): rules.make_trio_box,
        }

        func = func_map.get((bet_type, method))
        if not func:
            return JsonResponse({"error": f"未対応方式: {bet_type} {method}"}, status=400)

        # ✅ 関数実行
        kaime = func(new_entries, points)
        data["tickets"] = kaime

        # ===== ✅ 完成版JSON保存 =====
        save_dir = "data"
        os.makedirs(save_dir, exist_ok=True)

        place = data.get("place", "unknown")
        race_no = data.get("race", "unknown")
        today = datetime.now().strftime("%Y%m%d")

        # ファイル名：場名＋日付＋レース
        filename = f"{save_dir}/race_detail_{place}_{today}_{race_no}.json"

        # race_detail の古いデータを削除（上書き用）
        if os.path.exists(filename):
            os.remove(filename)
            print(f"🧹 古いファイルを削除しました: {filename}")

        # 保存（上書き）
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ 完成版保存: {filename}")
        #print(json.dumps(data, ensure_ascii=False, indent=2)) デバック用

        return JsonResponse(data, json_dumps_params={"ensure_ascii": False})

    except Exception as e:
        import traceback
        print("🚨 race_predict 例外:", e)
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)