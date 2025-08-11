import os
import re
import requests
from bs4 import BeautifulSoup

LINE_TOKEN   = os.getenv("LINE_TOKEN")
DENSUKE_URL  = "https://densuke.biz/list?cd=dxncu2PesTNses2c"
HTML_SNAPSHOT= "prev.html"

def fetch_html() -> str:
    r = requests.get(DENSUKE_URL, timeout=20)
    r.raise_for_status()
    return r.text

def send_broadcast(message: str):
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"messages":[{"type":"text","text":message}]}
    res = requests.post("https://api.line.me/v2/bot/message/broadcast",
                        headers=headers, json=payload, timeout=20)
    print("LINE API:", res.status_code, res.text)

# --- 日程だけを安全に抽出する ---
def extract_schedule_items(html: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")

    items: set[str] = set()

    # 1) セレクタで狙い撃ち（伝助でよくあるパターン）
    for th in soup.select("th.date, td.date"):
        txt = th.get_text(strip=True)
        if txt:
            items.add(txt)

    # 2) 万一セレクタで取れない場合は、日付っぽい行だけ正規表現で拾う
    #   例: 6月20日(木), 2025年7月3日(水)
    if not items:
        date_line_re = re.compile(r"(?:\d{4}年)?\s*\d{1,2}月\d{1,2}日（?.?）?")
        for line in soup.get_text("\n").splitlines():
            line = line.strip()
            if date_line_re.search(line):
                # 「表示日時」「最終更新」などは除外
                if any(ng in line for ng in ["表示日時", "更新", "Generated"]):
                    continue
                items.add(line)

    return items

def main():
    new_html = fetch_html()
    new_set  = extract_schedule_items(new_html)

    if not os.path.exists(HTML_SNAPSHOT):
        # 初回はスナップショット保存のみ
        with open(HTML_SNAPSHOT, "w", encoding="utf-8") as f:
            f.write(new_html)
        print(f"初回保存のみ: {len(new_set)} 件の候補を記録")
        return

    with open(HTML_SNAPSHOT, "r", encoding="utf-8") as f:
        old_html = f.read()
    old_set = extract_schedule_items(old_html)

    added = sorted(new_set - old_set)
    print(f"抽出: 旧{len(old_set)} / 新{len(new_set)} / 追加{len(added)}")

    for it in added:
        send_broadcast(f"📅 新しい日程が追加されました: {it}")

    # 次回比較用に更新
    with open(HTML_SNAPSHOT, "w", encoding="utf-8") as f:
        f.write(new_html)

if __name__ == "__main__":
    main()
