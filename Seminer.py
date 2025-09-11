# Seminer.py
import os, re, requests
from bs4 import BeautifulSoup

LINE_TOKEN    = os.getenv("LINE_TOKEN")
DENSUKE_URL   = "https://densuke.biz/list?cd=dxncu2PesTNses2c"
SNAPSHOT_HTML = os.getenv("SNAPSHOT_HTML") or "prev.html"  # 環境変数で上書き可

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DensukeWatcher/1.0; +https://github.com/)",
}

def fetch_html() -> str:
    r = requests.get(DENSUKE_URL, headers=HEADERS, timeout=20)
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
        print("[WARN] #listtable が見つかりません。ページ構造が変わった可能性があります。")
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

def chunk_messages(header: str, lines: list[str], limit: int = 4700) -> list[str]:
    current = header
    messages = []
    for line in lines:
        candidate = current + f"\n・{line}"
        if len(candidate) > limit:
            messages.append(current)
            current = header + f"\n・{line}"
        else:
            current = candidate
    if current.strip():
        messages.append(current)
    return messages

def send_broadcast_texts(texts: list[str]):
    if not LINE_TOKEN:
        print("[ERROR] 環境変数 LINE_TOKEN が未設定です（Messaging API のチャネルアクセストークンを設定してください）。")
        return
    url = "https://api.line.me/v2/bot/message/broadcast"  # ← Messaging API
    headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    for i in range(0, len(texts), 5):  # 1回リクエストで最大5件
        batch = [{"type":"text","text":t} for t in texts[i:i+5]]
        res = requests.post(url, headers=headers, json={"messages": batch}, timeout=20)
        print("LINE API:", res.status_code, res.text)

def main():
    try:
        new_html = fetch_html()
    except Exception as e:
        print(f"[ERROR] HTML取得に失敗: {e}")
        return

    new_keys, new_last = rows_from_html(new_html)

    # 初回は保存のみ
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

    notify_lines = [k for k in added if new_last.get(k, "") != "×"]
    print(f"[INFO] 通知対象（×除外）: {len(notify_lines)} 件")
    if notify_lines:
        header = "📅 新規枠が追加されました"
        messages = chunk_messages(header, notify_lines)
        send_broadcast_texts(messages)
    else:
        print("[INFO] 通知対象の追加はありませんでした。")

    with open(SNAPSHOT_HTML, "w", encoding="utf-8") as f:
        f.write(new_html)

if __name__ == "__main__":
    main()
