# generate_article.py
import json
import os
from datetime import datetime

CONFIG_PATH = "config.json"
FOOTER_PATH = "footer.md"
OUTPUT_DIR = "output"


def to_int(x):
    if x in (None, "", " "):
        return 0
    if isinstance(x, (int, float)):
        return int(x)
    return int(str(x).replace(",", "").replace("¥", "").strip())


def yen(x):
    """1500 → ￥1500円"""
    return f"￥{to_int(x):,}円"


def dash3(s):
    """'3-1-4' → '3-1-4'（半角ハイフン統一）"""
    s = str(s).strip()
    return "-".join(s.replace("＝", "-").replace("=", "-").split("-"))


def safe_basename(p):
    return os.path.basename(p) if p else ""


def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    title_date = None
    if config.get("raceset"):
        title_date = config["raceset"][0].get("date")
    if not title_date:
        title_date = datetime.now().strftime("%m月%d日")

    lines = []
    lines.append(f"# 🎯{title_date}ころがし結果まとめ🚤\n")

    for rs in config.get("raceset", []):
        character = rs.get("character", "")
        races = rs.get("race", [])
        race_count = len(races)

        lines.append(f"## {character}『{race_count}レースころがし🚤』\n")

        for idx, race in enumerate(races, start=1):
            name = race.get("name", "")
            round_ = race.get("round", "")
            numbers = dash3(race.get("3-ren", ""))
            odds = str(race.get("odds", "")).strip()
            get_val = to_int(race.get("get", 0))
            amount = to_int(race.get("amount", 0))
            ticket_num = str(race.get("ticket-num", "")).strip()
            purchase = to_int(race.get("purchase", 0))
            image = safe_basename(race.get("image", ""))

            emoji = "😊" if idx == 1 else "😎"
            lines.append(f"### ころがし{idx}レース目「{name}{round_}{emoji}」\n")

            if idx == 1:
                lines.append(f"**舟券金額**：{yen(amount)}以内")
            lines.append(f"**舟券数**：{ticket_num}点（各{yen(purchase)}）")
            lines.append(f"**買い目**：🎯{numbers}🎯 的中オッズ{odds}倍")
            lines.append(f"**払戻金**：{yen(get_val)}\n")
            lines.append(f"[画像：{image}]\n")

        total_get = to_int(races[-1].get("get", 0)) if races else 0
        lines.append(f"🎯**合計払戻金:{yen(total_get)}**🎯\n")

    if os.path.exists(FOOTER_PATH):
        with open(FOOTER_PATH, "r", encoding="utf-8") as f:
            footer_text = f.read().rstrip()
        lines.append(footer_text)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(
        OUTPUT_DIR, f"result_{datetime.now().strftime('%Y%m%d')}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ Markdown記事を出力しました → {out_path}")


if __name__ == "__main__":
    main()
