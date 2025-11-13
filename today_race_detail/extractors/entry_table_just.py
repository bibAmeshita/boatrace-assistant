#scraping/extractors/entry_table_just.py
from __future__ import annotations
from bs4 import BeautifulSoup
import re

# 全角→半角の置換テーブル（数字・ドット・マイナス・コロン・スペース・スラッシュ）
ZEN2HAN = str.maketrans("０１２３４５６７８９．－：　／", "0123456789.-: /")

def _t(el) -> str:
    """要素のテキストを取得して全角→半角へ寄せる"""
    return (el.get_text(" ", strip=True) if el else "").translate(ZEN2HAN)

def _to_int(s: str) -> int | None:
    s = (s or "").strip().translate(ZEN2HAN)
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else None

def _split_rates(cell_text: str):
    """
    '5.66 32.26 60.22' のような3値（勝率, 2連率, 3連率）をまとめて返す
    """
    s = cell_text.replace("\n", " ").replace("\r", " ")
    nums = re.findall(r"-?\d+(?:\.\d+)?", s.translate(ZEN2HAN))
    vals = [float(x) for x in nums[:3]] if nums else []
    while len(vals) < 3:
        vals.append(None)
    return tuple(vals[:3])

def _split_FL_ST(cell_text: str):
    """
    'F0 L0 0.18' → (F数, L数, 平均ST)
    """
    s = cell_text.replace("\n", " ").replace("\r", " ").translate(ZEN2HAN)
    mF  = re.search(r"F\s*(-?\d+)", s, re.IGNORECASE)
    mL  = re.search(r"L\s*(-?\d+)", s, re.IGNORECASE)
    mST = re.search(r"(-?\d+(?:\.\d+)?)\s*$", s)
    F  = int(mF.group(1)) if mF else None
    L  = int(mL.group(1)) if mL else None
    ST = float(mST.group(1)) if mST else None
    return F, L, ST

def _split_no_2r_3r(cell_text: str):
    """
    '70 31.58 48.42' → (No, 2連率, 3連率)
    """
    s = cell_text.replace("\n", " ").translate(ZEN2HAN)
    nums = re.findall(r"-?\d+(?:\.\d+)?", s)
    if not nums:
        return None, None, None
    no = int(float(nums[0]))
    r2 = float(nums[1]) if len(nums) > 1 else None
    r3 = float(nums[2]) if len(nums) > 2 else None
    return no, r2, r3

def extract_entries_from_racelist_just_html(html: str) -> list[dict]:
    """
    出走表（左ブロック）を全艇分抽出して返す。

    返却の各要素は以下のキーを持つ：
      lane, racer_id, racer_name, klass,
      branch, origin, age, weight,
      F, L, avg_st,
      national_win, national_2r, national_3r,
      local_win, local_2r, local_3r,
      motor_no, motor_2r, motor_3r,
      boat_no,  boat_2r,  boat_3r
    """
    soup = BeautifulSoup(html, "lxml")

    # 出走表テーブル（左ブロック）は .table1.is-tableFixed__3rdadd 内の最初の table
    race_table = soup.select_one(".table1.is-tableFixed__3rdadd table")
    if not race_table:
        return []

    entries: list[dict] = []

    # 各艇は tbody ごとにまとまっている（4行構成）— 直下のみを見る
    for tb in race_table.find_all("tbody", recursive=False):
        rows = tb.find_all("tr", recursive=False)
        if not rows:
            continue

        r0 = rows[0]
        tds = r0.find_all("td", recursive=False)
        # 左ブロックの最小列数を満たさない場合はスキップ（DOM差分対策）
        if len(tds) < 8:
            continue

        # 列の意味（現行DOM想定）
        # 0: 枠番
        # 1: 写真(リンク)
        # 2: 登録/級別・氏名・支部/出身・年齢/体重（divで段組）
        # 3: F/L/平均ST
        # 4: 全国 勝率/2連率/3連率
        # 5: 当地 勝率/2連率/3連率
        # 6: モーター No/2連率/3連率
        # 7: ボート   No/2連率/3連率
        # 8以降は右ブロックなので無視

        lane = _to_int(_t(tds[0]))

        # レーサー詳細（td[2]）
        td_info = tds[2]

        # 登録番号 / 級別（例: "3994 / B1"）
        num_grade = td_info.select_one(".is-fs11")
        racer_id = None
        klass = None
        if num_grade:
            nums = re.findall(r"\d+", _t(num_grade))
            racer_id = int(nums[0]) if nums else None
            m_cls = re.search(r"/\s*([AB]\d)", _t(num_grade))
            klass = m_cls.group(1) if m_cls else None

        # 氏名
        name_el = td_info.select_one(".is-fBold a") or td_info.select_one(".is-fBold")
        racer_name = _t(name_el)

        # 支部/出身地 と 年齢/体重（.is-fs11 が2つある想定なので最後のを使う）
        fs11s = td_info.select(".is-fs11")
        misc_el = fs11s[-1] if fs11s else None
        branch = origin = None
        age = weight = None
        if misc_el:
            text = _t(misc_el)  # 例: "滋賀/東京 46歳/46.5kg"
            m_br = re.search(r"([^\s/]+)/([^\s/]+)", text)
            if m_br:
                branch, origin = m_br.group(1), m_br.group(2)
            m_age = re.search(r"(\d+)\s*歳", text)
            m_w   = re.search(r"(\d+(?:\.\d+)?)\s*kg", text, re.IGNORECASE)
            age = int(m_age.group(1)) if m_age else None
            weight = float(m_w.group(1)) if m_w else None

        # F/L/平均ST
        F, L, avg_st = _split_FL_ST(_t(tds[3]))

        # 全国・当地・モーター・ボート
        national_win, national_2r, national_3r = _split_rates(_t(tds[4]))
        local_win,    local_2r,    local_3r    = _split_rates(_t(tds[5]))
        motor_no,     motor_2r,    motor_3r    = _split_no_2r_3r(_t(tds[6]))
        boat_no,      boat_2r,     boat_3r     = _split_no_2r_3r(_t(tds[7]))

        entries.append({
            "lane": lane,
            "racer_id": racer_id,
            "racer_name": racer_name,
            "klass": klass,
            "branch": branch,
            "origin": origin,
            "age": age,
            "weight": weight,
            "F": F,
            "L": L,
            "avg_st": avg_st,
            "national_win": national_win,
            "national_2r": national_2r,
            "national_3r": national_3r,
            "local_win": local_win,
            "local_2r": local_2r,
            "local_3r": local_3r,
            "motor_no": motor_no,
            "motor_2r": motor_2r,
            "motor_3r": motor_3r,
            "boat_no": boat_no,
            "boat_2r": boat_2r,
            "boat_3r": boat_3r,
        })

    # 安全のため枠番でソート
    entries.sort(key=lambda x: (x.get("lane") if x.get("lane") is not None else 99))
    return entries

def extract_before_entries_from_html(html: str) -> dict[int, dict]:
    """
    beforeinfo（直前情報）ページから以下を抽出:
      - weight, adjust_weight, exhibit_time, tilt, propeller, parts_change, last_result
      - course, st（右側のスタ展）
    """
    soup = BeautifulSoup(html, "lxml")
    result = {}

    # ===== 左のテーブル（体重・展示・チルト・部品・前走） =====
    table = soup.select_one(".is-w748")
    if table:
        for tbody in table.select("tbody"):
            lane_el = tbody.select_one("td.is-fs14")
            lane = _to_int(_t(lane_el)) if lane_el else None
            if not lane:
                continue

            # 各項目
            def _get_float(sel):
                el = tbody.select_one(sel)
                if not el:
                    return None
                text = _t(el)
                m = re.search(r"-?\d+(?:\.\d+)?", text)
                return float(m.group()) if m else None

            weight = _get_float("tr:nth-of-type(1) > td[rowspan='2']")
            adjust_weight = _get_float("tr:nth-of-type(3) > td[rowspan='2']")
            exhibit_time = _get_float("td[rowspan='4']:nth-of-type(5)")
            tilt = _get_float("td[rowspan='4']:nth-of-type(6)")

            propeller = _t(tbody.select_one("td[rowspan='4']:nth-of-type(7)"))
            propeller = None if not propeller or propeller == " " else propeller

            # 部品交換
            parts_el = tbody.select_one("td.is-p5-5 ul.labelGroup1")
            parts_change = None
            if parts_el:
                texts = [li.get_text(strip=True) for li in parts_el.select("li")]
                parts_change = " ".join(texts) if texts else None

            # 前走成績（R / 進入 / ST / 着順を連結）
            rows = [r.find_all("td") for r in tbody.find_all("tr")]
            last_result_parts = []
            for r in rows:
                for td in r:
                    text = _t(td)
                    if text and text not in ("&nbsp;", " "):
                        last_result_parts.append(text)
            last_result = " ".join(last_result_parts)

            result[lane] = {
                "weight": weight,
                "adjust_weight": adjust_weight,
                "exhibit_time": exhibit_time,
                "tilt": tilt,
                "propeller": propeller,
                "parts_change": parts_change,
                "last_result": last_result.strip() or None,
                "course": None,
                "st": None,
            }

    # ===== 右側スタ展テーブル（course, st） =====
    start_table = soup.select_one(".is-w238")
    if start_table:
        tmp = {}
        for div in start_table.select(".table1_boatImage1"):
            num_el = div.select_one(".table1_boatImage1Number")
            lane = _to_int(_t(num_el)) if num_el else None
            if not lane:
                continue

            st_el = div.select_one(".table1_boatImage1Time")
            st = None
            if st_el:
                s = _t(st_el)
                if s.startswith("."):
                    s = "0" + s
                try:
                    st = float(s)
                except ValueError:
                    st = None

            left_val = None
            boat_el = div.select_one(".table1_boatImage1Boat")
            if boat_el and boat_el.has_attr("style"):
                m = re.search(r"left:\s*([\d.]+)%", boat_el["style"])
                if m:
                    left_val = float(m.group(1))

            tmp[lane] = {"left": left_val, "st": st}

        # left の昇順で course を決定
        sorted_lanes = sorted(
            [ (ln, v["left"]) for ln, v in tmp.items() if v["left"] is not None ],
            key=lambda x: x[1]
        )
        for i, (ln, _) in enumerate(sorted_lanes, start=1):
            if ln in result:
                result[ln]["course"] = i
                result[ln]["st"] = tmp[ln]["st"]

    return result

def extract_weather_meta_from_html(html: str):
    soup = BeautifulSoup(html, "html.parser")

    def _get_text(selector):
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    def _to_float(value):
        if not value:
            return None
        try:
            return float(re.sub(r"[^0-9.]", "", value))
        except ValueError:
            return None

    # --- 風向 ---
    wind_el = soup.select_one(".is-windDirection .weather1_bodyUnitImage")
    wind_angle = _extract_angle_from_class(wind_el, "is-wind") if wind_el else None
    relative = get_relative_wind_label(wind_angle)

    # --- 天候情報 ---
    meta = {
        "weather": _get_text(".is-weather .weather1_bodyUnitLabelTitle"),  # ←修正済み
        "temperature": _to_float(_get_text(".is-direction .weather1_bodyUnitLabelData")),
        "water_temp": _to_float(_get_text(".is-waterTemperature .weather1_bodyUnitLabelData")),
        "wind_speed": _to_float(_get_text(".is-wind .weather1_bodyUnitLabelData")),
        "wave_height": _to_float(_get_text(".is-wave .weather1_bodyUnitLabelData")),
        "wind_angle": wind_angle,
        "wind_dir_str": None,
        **relative
    }
    return meta

def get_relative_wind_label(wind_angle: int) -> dict:
    """
    wind_angle: is-wind1〜16（矢印方向＝風の吹く方向）
    戻り値:
      relative_wind: 「追い風・右追い風・右横風・右向かい風・向かい風・左向かい風・左横風・左追い風」
      relative_angle: 右進行を0°とした角度（例: 0=追い風、180=向かい風）
    """
    if not wind_angle:
        return {"relative_wind": None, "relative_angle": None}

    # 22.5°単位の角度に変換
    deg = (wind_angle - 1) * 22.5
    from_deg = (deg + 180) % 360
    relative_angle = (from_deg - 90) % 360  # 右方向を0°基準とする

    # 8分割の風ラベル（45°刻み）
    if 337.5 <= relative_angle or relative_angle < 22.5:
        label = "追い風"
    elif 22.5 <= relative_angle < 67.5:
        label = "右追い風"
    elif 67.5 <= relative_angle < 112.5:
        label = "右横風"
    elif 112.5 <= relative_angle < 157.5:
        label = "右向かい風"
    elif 157.5 <= relative_angle < 202.5:
        label = "向かい風"
    elif 202.5 <= relative_angle < 247.5:
        label = "左向かい風"
    elif 247.5 <= relative_angle < 292.5:
        label = "左横風"
    else:
        label = "左追い風"

    return {"relative_wind": label, "relative_angle": round(relative_angle, 1)}

# --- 以下、補助関数群を同ファイル内に追加 ---

def _extract_angle_from_class(el, prefix):
    """例: class='weather1_bodyUnitImage is-wind5' → 5"""
    for cls in el.get("class", []):
        if cls.startswith(prefix):
            num = re.sub(r"\D", "", cls)
            if num.isdigit():
                return int(num)
    return None
