import requests
from bs4 import BeautifulSoup
import time
import re
from trafilatura import extract


def fetch_hatena_news_entries():
    url = "https://b.hatena.ne.jp/hotentry/it"
    max_attempts = 5
    attempt_count = 0
    entries = []
    while attempt_count < max_attempts:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            entry_elements = soup.select("li.entrylist-image-entry .entrylist-contents")
            entry_elements += soup.select(".js-hotentries .entrylist-contents")
            # print("entry_elements件数:", len(entry_elements))
            seen = set()
            for el in entry_elements:
                anchor = el.select_one(
                    "h3.entrylist-contents-title a"
                ) or el.select_one("a")
                date_el = el.select_one(
                    "ul.entrylist-contents-meta li.entrylist-contents-date"
                )
                date = date_el.get_text(strip=True) if date_el else ""
                users_el = el.select_one("span.entrylist-contents-users a span")
                users = users_el.get_text(strip=True) if users_el else ""
                if not users:
                    users_container = el.select_one("span.entrylist-contents-users")
                    if users_container:
                        match = re.search(r"(\d+)", users_container.get_text())
                        if match:
                            users = match.group(1)
                if anchor and anchor.get("href") not in seen:
                    seen.add(anchor.get("href"))
                    entries.append(
                        {
                            "title": anchor.get_text(strip=True),
                            "url": anchor.get("href"),
                            "date": date,
                            "users": users,
                        }
                    )
            # print("entries件数:", len(entries))
            # with open("hatena_debug.html", "w", encoding="utf-8") as f:
            #     f.write(response.text)
            break
        except Exception as e:
            attempt_count += 1
            print(
                f"fetchHatenaNewsEntries 内でエラーが発生しました (試行 {attempt_count}): {e}"
            )
            if attempt_count >= max_attempts:
                print("最大試行回数に達しました。処理を中断します。")
                raise
            else:
                print("再試行します...")
                time.sleep(2)
    return entries


def fetch_article_content_from_url(url):
    try:
        response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            print(f"HTTPエラー: {response.status_code}")
            return ""
        html = response.text
        article = extract(html, favor_precision=True)
        return article if article else ""
    except Exception as e:
        print(f"エラー: {e}")
        return ""
