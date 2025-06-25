import os
import datetime
from hatena_scraper import fetch_hatena_news_entries, fetch_article_content_from_url
from history_manager import (
    load_history,
    save_history_json,
    load_history_json,
)
from utils import simple
from post_note import main as post_note
import asyncio
import sys

# noteの心得.mdのパス
NOTE_KOKOROE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "public", "noteの心得.md"
)
# noteの心得.mdのパス
NOTE_SAMPLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "public", "サンプル.md"
)

RANK_LIMIT = 5


def main(publish=False):
    entries = fetch_hatena_news_entries()
    if not entries:
        print("エントリーが見つかりませんでした。セレクタを確認してください。")
        return

    now = datetime.datetime.now()
    # historyディレクトリをsrcの一つ上のディレクトリに指定
    history_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history")
    os.makedirs(history_dir, exist_ok=True)
    history_filename = os.path.join(
        history_dir, f"history_{now.year}_{now.month:02d}_{now.day:02d}.txt"
    )

    history = load_history(history_filename)
    top_entries = [item for item in entries if item["title"] not in history][:20]
    news_titles_text = ""
    for idx, item in enumerate(top_entries):
        news_titles_text += f"{idx+1}. {item['title']} ({item['date']}) {item['users']} USERS\n{item['url']}\n\n"

    # print("ニュースタイトルリスト:\n", news_titles_text)
    # send_to_google_chat(summary_text + news_titles_text)

    # rank, usersも含めてjson保存（usersはint型で保存）
    json_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "history", "json"
    )
    os.makedirs(json_dir, exist_ok=True)
    json_filename = os.path.join(
        json_dir,
        f"news_{now.year}_{now.month:02d}_{now.day:02d}_{now.hour:02d}_{now.minute:02d}.json",
    )
    entries_for_json = []
    # noteの心得.mdを読み込む
    with open(NOTE_KOKOROE_PATH, encoding="utf-8") as f:
        note_kokoroe = f.read()
        # print(note_kokoroe)
    with open(NOTE_SAMPLE_PATH, encoding="utf-8") as f:
        note_sample = f.read()
    for idx, item in enumerate(entries):
        try:
            users_num = int(item["users"].replace(",", "")) if item["users"] else 0
        except Exception:
            users_num = 0
        entry = {
            "rank": idx + 1,
            "url": item["url"],
            "title": item["title"],
            "users": users_num,
        }

        summary = ""
        if idx < RANK_LIMIT and item["url"]:
            urlBody = fetch_article_content_from_url(item["url"])
            summary = simple(
                topic=f"あなたはプロのライターです。タイトルから記事で一番伝えたい部分を考察し、300文字以内で要約してください。先頭や文末に～をまとめましたや改行などの情報は不要です。\nタイトル: {item['title']}\n記事: {urlBody}",
                # model="gemini-2.5-flash-preview-04-17",
            )
            if summary:
                entry["summary"] = summary
        if idx < RANK_LIMIT:
            entries_for_json.append(entry)
    save_history_json(json_filename, entries_for_json)

    history_list = load_history_json(json_filename)
    markdown = simple(
        topic=f"次のJsonでまとめた記事をNoteに投稿するのでmarkdownにしてください。先頭や文末に～をまとめましたや```markdown、などの情報は不要です。箇条書きの1行は大体36文字(64byte)なのでそれ以下にしてください。\n【構成は下記のサンプルを意識してください】\n{note_sample}\n\n【記事】\n{history_list}",
        # topic=f"次のJsonでまとめた記事をNoteに投稿するのでmarkdownにしてください。先頭や文末に～をまとめました、などの情報は不要です。\n【書き方はコチラを意識してください】\n{note_kokoroe}\n\n【記事】\n{history_list}",
    )
    # print(markdown)

    # markdownをhistory/mdディレクトリに保存
    md_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history", "md")
    os.makedirs(md_dir, exist_ok=True)
    md_filename = os.path.join(
        md_dir,
        f"news_{now.year}_{now.month:02d}_{now.day:02d}_{now.hour:02d}_{now.minute:02d}.md",
    )
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(markdown)

    asyncio.run(post_note(md_filename, headless=False, publish=publish))


if __name__ == "__main__":
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else None
    if arg == "true":
        publish = True
    else:
        publish = False
    main(publish=publish)
