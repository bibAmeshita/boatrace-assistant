#today_race_detail/extractors/entry_table_just.py
from __future__ import annotations
from bs4 import BeautifulSoup
import re
import os


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
    print(f"👉直前情報得開始")
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


def extract_before_entries_from_html(html: str):
    print("👉スタート展示取得開始（左側＋右側まとめて抽出）")

    try:
        soup = BeautifulSoup(html, "html.parser")

        # -------------------------
        # ① 左側テーブル抽出
        # -------------------------
        left = {}
        table = soup.select_one(".is-w748")
        if not table:
            print("❌ .is-w748 テーブルが見つかりません")
            return {}

        tbodies = table.select("tbody.is-fs12")

        for tbody in tbodies:
            trs = tbody.find_all("tr")
            if not trs:
                continue

            first_tr = trs[0]
            cells = first_tr.find_all("td")

            if len(cells) < 8:
                continue

            lane = int(cells[0].text.strip())
            weight = _t(cells[3])
            exhibit_time = _t(cells[4])
            tilt = _t(cells[5])
            propeller = _t(cells[6])
            parts_change = _parse_parts_change(cells[7])
            last_result = None  # 今回は未使用

            left[lane] = {
                "weight": _to_float(weight),
                "adjust_weight": None,
                "exhibit_time": _to_float(exhibit_time),
                "tilt": _to_float(tilt),
                "propeller": propeller if propeller.strip() else None,
                "parts_change": parts_change,
                "last_result": last_result,
            }

        # -------------------------
        # ② 右側（ST・コース）抽出
        # -------------------------
        #print("👉右側 ST 抽出テスト開始")

        st_divs = soup.select("div.table1_boatImage1")

        right = {}

        for idx, div in enumerate(st_divs, start=1):

            # 進入コース（色で決まる）
            course = idx

            # ST 解析
            spans = div.find_all("span")
            time_tag = div.select_one(".table1_boatImage1Time")
            st_raw = time_tag.get_text(strip=True) if time_tag else ""

            parsed = parse_st_value(st_raw)

            right[idx] = {
                "course": course,
                "st": parsed["st"],
                "is_flying": parsed["is_flying"],
                "is_late": parsed["is_late"],
            }

        # -------------------------
        # ③ 左＋右を lane ごとに統合
        # -------------------------
        merged = {}

        all_lanes = set(left.keys()) | set(right.keys())
        for lane in sorted(all_lanes):
            merged[lane] = {
                **left.get(lane, {}),
                **right.get(lane, {}),
            }

        #print("👉 最終 merged =", merged)

        # -------------------------
        # ④ merged の各 lane に exhibit_info をまとめる
        # -------------------------
        for lane, entry in merged.items():
            entry["exhibit_info"] = {
                "adjust_weight": entry.pop("adjust_weight", None),
                "exhibit_time": entry.pop("exhibit_time", None),
                "tilt": entry.pop("tilt", None),
                "propeller": entry.pop("propeller", None),
                "parts_change": entry.pop("parts_change", None),
                "last_result": entry.pop("last_result", None),
                "course": entry.pop("course", None),
                "st": entry.pop("st", None),
                "is_flying": entry.pop("is_flying", None),
                "is_late": entry.pop("is_late", None),
            }

        return merged

    except Exception as e:
        import traceback
        print("🚨 extract_before_entries_from_html 例外:", e)
        traceback.print_exc()
        return {}





def extract_weather_meta_from_html(html: str):
    print(f"👉水面気象報得開始")

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
      relative_wind: 風向き8方位のラベル
      relative_angle: 右方向を0°とした角度
    """
    if not wind_angle:
        return {"relative_wind": None, "relative_angle": None}

    # --- 角度計算（TO方向＝矢印の指す方向） ---
    deg = (wind_angle - 1) * 22.5  # 0°=真上, 90°=右, 180°=下, 270°=左
    relative_angle = (deg - 90) % 360  # 右向きを0°基準にする

    # --- 8方向ラベル ---
    if 337.5 <= relative_angle or relative_angle < 22.5:
        label = "追い風（完全）"

    elif 22.5 <= relative_angle < 67.5:
        label = "斜め追い風（アウト→イン寄り）"

    elif 67.5 <= relative_angle < 112.5:
        label = "横風（アウト→イン）"

    elif 112.5 <= relative_angle < 157.5:
        label = "斜め向かい風（アウト→イン寄り）"

    elif 157.5 <= relative_angle < 202.5:
        label = "向かい風（完全）"

    elif 202.5 <= relative_angle < 247.5:
        label = "斜め向かい風（イン→アウト寄り）"

    elif 247.5 <= relative_angle < 292.5:
        label = "横風（イン→アウト）"

    else:
        label = "斜め追い風（イン→アウト寄り）"

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


def parse_st_value(st_raw: str | None):
    """
    STを float + フライング/出遅れフラグ に分解して返す

    戻り値:
      {
        "st": float or None,
        "is_flying": bool,
        "is_late": bool,
      }
    """
    if not st_raw:
        return {"st": None, "is_flying": False, "is_late": False}

    s = st_raw.strip()

    # 文字による明示 ("フライング", "出遅れ")
    if s == "フライング":
        return {"st": None, "is_flying": True, "is_late": False}

    if s == "出遅れ":
        return {"st": None, "is_flying": False, "is_late": True}

    is_flying = s.startswith("F")
    is_late = s.startswith("L")

    # F.03 → 0.03, L.02 → 0.02
    if is_flying or is_late:
        s = s[1:]  # F/L を取り除く

    # ".04" → "0.04"
    if s.startswith("."):
        s = "0" + s

    try:
        st_value = float(s)
    except:
        st_value = None

    return {
        "st": st_value,
        "is_flying": is_flying,
        "is_late": is_late,
    }


def _t(tag):
    return tag.text.strip() if tag and tag.text else ""


def _to_float(val):
    try:
        return float(val.replace("kg", "").replace("cm", "").replace("m", "").strip())
    except Exception:
        return None


def _parse_parts_change(tag):
    """部品交換欄"""
    if not tag:
        return None
    items = [li.text.strip() for li in tag.select("li span") if li.text.strip()]
    return items or None

def _parse_last_result(tbody):
    """前走成績欄 (R / 進入 / ST / 着順) を1行文字列でまとめる"""
    rows = tbody.select("tr")
    texts = []
    for r in rows:
        tds = r.select("td")
        if not tds:
            continue
        row_text = " ".join(td.text.strip() for td in tds if td.text.strip())
        if row_text:
            texts.append(row_text)
    return " ".join(texts) if texts else None