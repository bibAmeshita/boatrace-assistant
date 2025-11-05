from bs4 import BeautifulSoup
import re

ZEN_TO_HAN = str.maketrans("０１２３４５６７８９：　／", "0123456789: /")

def _safe_text(el) -> str:
    return (el.get_text(" ", strip=True) if el else "").translate(ZEN_TO_HAN)

def extract_race_meta_from_html(html: str, race_url: str = "") -> dict:
    """
    レース詳細スクレイピング（必要最小限）
    取得：
    - date_text: 例 "9月8日"
    - day_text: 例 "３日目"
    - type: 例 "予選"
    - distance: 例 "1800m"
    """

    soup = BeautifulSoup(html, "lxml")

    # ▼ 開催日 & ○日目
    active_tab = soup.select_one(".tab2.is-type1__3rdadd .tab2_tabs li.is-active2 .tab2_inner")
    date_text = day_text = ""
    if active_tab:
        outer_text = active_tab.contents[0].strip() if active_tab.contents else _safe_text(active_tab)
        date_text = outer_text.translate(ZEN_TO_HAN)
        inner_span = active_tab.find("span")
        day_text = _safe_text(inner_span)

    # ▼ 種別 & 距離 (例: "予選 1800m")
    h3 = _safe_text(soup.select_one(".title16__add2020 h3"))
    h3_norm = re.sub(r"\s+", " ", h3).strip()

    race_type = ""
    distance = ""
    m = re.search(r"([^\s]+)\s+(\d+ ?m)", h3_norm)
    if m:
        race_type = m.group(1)
        distance = m.group(2).replace(" ", "")

    return {
        "date_text": date_text,
        "day_text": day_text,
        "type": race_type,
        "distance": distance,
    }