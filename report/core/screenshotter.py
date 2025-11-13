# report/core/screenshotter.py
from playwright.sync_api import sync_playwright
from PIL import Image
import os, math, json, sys, datetime
from pathlib import Path


# --- プロジェクトルートを自動特定 ---
BASE_DIR = Path(__file__).resolve().parents[2]  # report/core/ → report/ → project_root/
DATA_DIR = BASE_DIR / "data"
CONFIG_PATH = DATA_DIR / "report.json"

print(f"🟢 Screenshotter started at {datetime.datetime.now()} in {os.getcwd()}", flush=True)
print(f"📄 CONFIG_PATH = {CONFIG_PATH}", flush=True)

# === JSON読み込み ===
if not CONFIG_PATH.exists():
    print(f"❌ 設定ファイルが見つかりません: {CONFIG_PATH}", flush=True)
    exit(1)


with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for raceset in config["raceset"]:
        print(f"=== 🎯 {raceset['character']} のレースセット開始 ({raceset['date']}) ===")

        for race in raceset["race"]:
            url = race["page"]
            if not url:
                continue

            print(f"→ {url}")

            # ---- ページ読み込み ----
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            # ネットワークの完全静止は待たない（ポーリング等で固まるため）
            # 代わりに「必要な要素が出るまで」ピンポイント待機
            page.wait_for_selector("div.heading2_area img", timeout=60000)
            page.wait_for_selector("div.table1.h-mt10", timeout=60000)



            # ---- 締切予定時刻（青い列の下） ----
            try:
                active_th = page.locator("div.table1.h-mt10 thead th:not([class])").first
                index = active_th.evaluate(
                    "el => Array.from(el.parentElement.children).indexOf(el) + 1"
                )
                td_selector = f"div.table1.h-mt10 tbody tr td:nth-child({index})"
                race_time = page.locator(td_selector).inner_text().strip()
                race["time"] = race_time
            except Exception as e:
                print(f"⚠️ time取得失敗: {e}")
                race["time"] = ""


            # ---- スクリーンショット ----
            screenshot_dir = DATA_DIR / "screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)
            base_filename = f"{raceset['date']}_{raceset['character']}_{race['name']}_{race['round']}"
            combined_path = screenshot_dir / f"{base_filename}.png"

            part1 = page.locator("div.grid.is-type2.h-clear.h-mt10 >> div.grid_unit").first
            part2 = page.locator("div.grid.is-type2.h-clear:not(.h-mt10) >> div.grid_unit").first

            part1_path = str(combined_path).replace(".png", "_1.png")
            part2_path = str(combined_path).replace(".png", "_2.png")
            part1.screenshot(path=part1_path)
            part2.screenshot(path=part2_path)

            img1, img2 = Image.open(part1_path), Image.open(part2_path)
            width, height = max(img1.width, img2.width), img1.height + img2.height
            combined = Image.new("RGB", (width, height))
            combined.paste(img1, (0, 0))
            combined.paste(img2, (0, img1.height))
            combined.save(combined_path)

            race["image"] = str(combined_path)

            os.remove(part1_path)
            os.remove(part2_path)

            print(f"✅ {race['name']} {race['round']} 取得完了 → {combined_path}")

        print(f"=== {raceset['character']} のセット完了 ===\n")

    browser.close()

with open(CONFIG_PATH, "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print("💾 report.json に更新を書き戻しました！")