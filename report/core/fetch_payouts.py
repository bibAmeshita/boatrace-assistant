# report/core/fetch_payouts.py
import re
import requests
from bs4 import BeautifulSoup

PAY_URL = "https://www.boatrace.jp/owpc/pc/race/pay"


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.text


def parse_all_venues_as_dict(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    tables = soup.select("div.table1 > table.is-strited1.is-wAuto")
    if not tables:
        return result

    for tbl in tables:
        # 場名
        venue_cells = tbl.select("thead tr:nth-of-type(1) th[colspan]")
        venues = []
        for th in venue_cells:
            img = th.select_one(".table1_areaName img[alt]")
            venues.append(img["alt"].strip() if img else "不明")

        for v in venues:
            result.setdefault(v, [])

        tbodies = tbl.select("tbody")
        for r_index, tbody in enumerate(tbodies, start=1):
            tr = tbody.select_one("tr")
            if not tr:
                continue

            race_label = tr.select_one("th")
            race = race_label.get_text(strip=True) if race_label else f"{r_index}R"

            tds = tr.select("td")
            for i, venue in enumerate(venues):
                base = i * 3
                if base + 2 >= len(tds):
                    continue

                td_combo = tds[base]
                td_pay = tds[base + 1]
                td_pop = tds[base + 2]

                # ✅ data-href（詳細ページURL）取得
                href = td_combo.get("data-href", "")
                if href.startswith("/"):
                    href = "https://www.boatrace.jp" + href

                # 組番
                nums = [span.get_text(strip=True) for span in td_combo.select(".numberSet1_number")]
                combo = "-".join(nums) if nums else ""

                # 払戻金
                pay_text = td_pay.get_text(strip=True).replace("　", " ")
                m_pay = re.search(r"(\d[\d,]*)", pay_text)
                pay_num = int(m_pay.group(1).replace(",", "")) if m_pay else 0

                # 人気
                pop_text = td_pop.get_text(strip=True)
                if pop_text == "返":
                    pop_display = "返"
                else:
                    m_pop = re.search(r"\d+", pop_text)
                    pop_display = m_pop.group(0) if m_pop else ""

                # 倍率
                odds_suffix = f"（{round(pay_num / 100, 2)}倍）" if pay_num > 0 else ""

                if not combo or not pay_text:
                    continue

                # 人気表記
                pop_suffix = f"({pop_display}番人気)" if pop_display not in ("", "返") else "(返)" if pop_display == "返" else ""

                # ✅ href を含めて格納
                result[venue].append(
                    (race, combo, pay_text, odds_suffix, pop_suffix, href)
                )

    return result


def fetch_payouts():
    """boatrace.jpから払戻データを取得して venues 辞書を返す"""
    html = fetch_html(PAY_URL)
    venue_dict = parse_all_venues_as_dict(html)
    return venue_dict


def fetch_payouts_with_time():
    """払戻データに開始時間をマージして返す"""
    from today_races.models import DailyRaceCache
    import json

    # 1️⃣ 払戻データ取得
    payouts = fetch_payouts()

    # 2️⃣ 今日のレースデータ（時間付き）を取得
    cache = DailyRaceCache.objects.first()
    if not cache:
        print("⚠️ DailyRaceCache が存在しません。時間は付与されません。")
        return payouts

    daily_data = json.loads(cache.json_text)

    # 3️⃣ 「場名＋レース番号」→ 時間 のマップを作成
    time_map = {}
    for venue in daily_data:
        name = venue["place"]
        for race in venue["races"]:
            key = f"{name}{race['rno']}"   # 例: "戸田3R"
            time_map[key] = race["time"]

    # 4️⃣ 払戻データに時間を追加して再構築
    merged = {}
    for venue, rows in payouts.items():
        new_rows = []
        for race, combo, pay_text, odds_suffix, pop_suffix, href in rows:
            time = time_map.get(f"{venue}{race}", "")
            new_rows.append((race, combo, pay_text, odds_suffix, pop_suffix, time, href))
        merged[venue] = new_rows

    return merged