import requests
import os
import difflib
from bs4 import BeautifulSoup

LINE_TOKEN = os.getenv("LINE_TOKEN")
DENSUKE_URL = "https://densuke.biz/list?cd=dxncu2PesTNses2c"
HTML_FILE = "prev.html"

def fetch_html():
    res = requests.get(DENSUKE_URL)
    return res.text

def send_broadcast(message):
    headers = {
        "Authorization": f"Bearer {os.environ['LINE_TOKEN']}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    res = requests.post("https://api.line.me/v2/bot/message/broadcast",
                        headers=headers, json=payload)

    print("✅ LINE APIレスポンス:")
    print(f"Status Code: {res.status_code}")
    print(f"Response Body: {res.text}")

def extract_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    return [line.strip() for line in soup.get_text().splitlines() if line.strip()]



def main():
    new_html = fetch_html()
    if not os.path.exists(HTML_FILE):
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(new_html)
        print("初回保存のみ")
        return

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        old_html = f.read()

    old_lines = extract_text(old_html)
    new_lines = extract_text(new_html)

    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
    added = [l[1:] for l in diff if l.startswith("+") and not l.startswith("+++")]

    new_items = [l for l in added if any(c.isdigit() for c in l)]

    for item in new_items:
        send_broadcast(f"📅 新しい予定が追加されました: {item}")

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(new_html)
        
        
    send_broadcast("✅ テスト通知：GitHub ActionsからのLINE通知テストです！")

if __name__ == "__main__":
    main()
