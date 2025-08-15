import os, re, requests
from bs4 import BeautifulSoup

LINE_TOKEN   = os.getenv("LINE_TOKEN")
DENSUKE_URL  = "https://densuke.biz/list?cd=dxncu2PesTNses2c"
SNAPSHOT_HTML= "prev.html"  # ← HTMLを保存

def fetch_html() -> str:
    r = requests.get(DENSUKE_URL, timeout=20)
    r.raise_for_status()
    return r.text

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def rows_from_html(html: str):
    """
    #listtable のデータ行を (行キー, 最終セルの記号) で抽出
    - 行キー: 1列目(例: "13日（水）14：00～")
    - 最終セルに '×' を含むなら '×' を返す
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("#listtable")
    if not table:
        return set(), {}

    rows = table.find_all("tr")
    keys, lastmap = set(), {}
    for tr in rows[1:]:  # ヘッダ行スキップ
        cells = tr.find_all(["td","th"])
        if not cells or not tr.find("td"):
            continue
        first = norm(cells[0].get_text(" ", strip=True))
        if not first or set(first) == {"-"}:  # 仕切り行 "------" は除外
            continue
        last_text = norm(cells[-1].get_text(" ", strip=True))
        last = "×" if "×" in last_text else last_text
        keys.add(first)
        lastmap[first] = last
    return keys, lastmap

def send_broadcast(message: str):
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    payload = {"messages":[{"type":"text","text":message}]}
    res = requests.post(url, headers=headers, json=payload, timeout=20)
    print("LINE API:", res.status_code, res.text)

def main():
    new_html = fetch_html()
    new_keys, new_last = rows_from_html(new_html)

    if not os.path.exists(SNAPSHOT_HTML):
        with open(SNAPSHOT_HTML, "w", encoding="utf-8") as f:
            f.write(new_html)
        print(f"[INFO] 初回保存のみ（行 {len(new_keys)} 件）")
        return

    with open(SNAPSHOT_HTML, "r", encoding="utf-8") as f:
        old_html = f.read()
    old_keys, _ = rows_from_html(old_html)

    added = sorted(new_keys - old_keys)
    print(f"[INFO] 旧{len(old_keys)} / 新{len(new_keys)} / 追加{len(added)}")

    for k in added:
        if new_last.get(k, "") == "×":
            print(f"[SKIP] {k}（最後のセルが×）")
            continue
        send_broadcast(f"📅 新規枠が追加: {k}")

    # 次回比較用に最新HTMLを保存
    with open(SNAPSHOT_HTML, "w", encoding="utf-8") as f:
        f.write(new_html)

if __name__ == "__main__":
    main()
