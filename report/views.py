# report/views.py
from django.shortcuts import render
from django.http import JsonResponse
import json, os, subprocess, sys, traceback
from report.core.fetch_payouts import fetch_payouts_with_time
from ui.models import Character

def report(request):
    error = None
    venues = None
    if request.method == "POST":
        try:
            venues = fetch_payouts_with_time()
        except Exception as e:
            error = str(e)

    characters = Character.objects.all().values('name', 'tone', 'prediction', 'index')

    context = {
        "venues": venues,
        "error": error,
        "characters": list(characters),
        "range_list": range(1, 13),
    }
    return render(request, "report.html", context)


def save_report(request):
    if request.method == "POST":
        try:
            # === JSON保存 ===
            data = json.loads(request.body)
            file_path = os.path.join(os.path.dirname(__file__), "../data/report.json")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # === スクリーンショットスクリプト起動 ===
            script_path = os.path.join(os.path.dirname(__file__), "core/screenshotter.py")
            print(f"🟢 実行予定: {script_path}", flush=True)

            # Python実行パスを明示して、ログ出力もリダイレクト
            log_path = os.path.join(os.path.dirname(__file__), "../data/screenshotter.log")
            with open(log_path, "a", encoding="utf-8") as log:
                subprocess.Popen(
                    [sys.executable, script_path],
                    cwd=os.path.dirname(script_path),
                    stdout=log,
                    stderr=log,
                )

            print(f"✅ screenshotter 起動コマンドを送信しました。", flush=True)
            return JsonResponse({"status": "ok"})

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid method"}, status=400)