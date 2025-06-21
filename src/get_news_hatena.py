import os
from datetime import datetime, timedelta
from hatena_scraper import fetch_hatena_news_entries, fetch_article_content_from_url
from history_manager import (
    load_history,
    save_history_json,
)
from utils import simple
from post_note import main as post_note
from typing import List, Dict
import asyncio
import sys
import random

ALL_RANK = 7
DEFAULT_RANK_LIMIT = 3
RANK_LIMIT = DEFAULT_RANK_LIMIT

# 魚拓シリーズに使える絵文字のリスト
emoji_list = [
    "🎣",
    "🎣",
    "🎣",
    "🎣",
    "🎣",
    "🎣",
    "🎣",
    "🎣",
    "🎣",
    "🎣",  # 釣り多めに
    "🐟",
    "🐠",
    "🦑",
    "🐡",
    "🐙",
    "🦐",
    "🐳",
    "🪼",  # 拡張：海系＋水中生物
]

# ランダムに1つ選ぶ
chosen_emoji = random.choice(emoji_list)
TEMPLATE_TITLE = (
    # f""
    f"### {datetime.now().month}/{datetime.now().day}IT速報{chosen_emoji}｜"
    # f"# 【{datetime.now().month}/{datetime.now().day} 技術魚拓{chosen_emoji}】"
)


# 各ランキングごとの要約プロンプト
ARTICLE_SUMMARY_PROMPT = [
    """あなたはプロのライターです。
タイトルから記事で一番伝えたい部分を考察し、
1行目に自分なりのタイトルを20文字程度で、
2~4行目の3行に・から始まる箇条書き（記号なし）で1行は40文字(80byte)なのでそれ以下、
5行目以降に300文字以内で要約してください。
先頭や文末に～をまとめましたや改行などの情報は不要です。""",
    """あなたはプロのライターです。
タイトルから記事で一番伝えたい部分を考察し、
1行目に自分なりのタイトルを先頭に絵文字付きで20文字程度で、
2~4行目の3行に・から始まる箇条書き（記号なし）で1行は40文字(80byte)なのでそれ以下、
5行目以降に300文字以内で要約してください。
先頭や文末に～をまとめましたや改行などの情報は不要です。""",
]

# 全体評価プロンプト
ARTICLE_EVALUATION_PROMPT = [
    """次のまとめた記事を総評してください。1行目はランキングの中から最も目立つ or 役立ちそうな内容を一つに絞ってタイトルを60文字程度でトレンドに沿ってとっても刺激的に記載してください。以降の行は総評を記載してください。箇条書きの場合は（記号なし）で1行は30文字(60byte)なのでそれ以下。後半には決まり文句と、最後の行にはハッシュタグを記載してください。
先頭や文末に～をまとめましたや```markdown、などの情報は不要です。""",
    """次のまとめた記事を総評してください。1行目はキャッチーでNo.1~3に沿った記事のタイトルを記号を使いながら全角70~90文字で記載してください。以降の行は総評を記載してください。箇条書きの場合は（記号なし）で1行は30文字(60byte)なのでそれ以下。後半には決まり文句と、最後の行にはハッシュタグを記載してください。
先頭や文末に～をまとめましたや```markdown、などの情報は不要です。""",
]
# topic=f"""次のまとめた記事を総評して1行目に記事のタイトルをキャッチーなアイデアで、以降は総評を記載してください。箇条書きの場合は（記号なし）で1行は30文字(60byte)なのでそれ以下。後半には決まり文句と、最後の行にはハッシュタグを記載してください。

# noteの心得.mdのパス
NOTE_KOKOROE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "public", "noteの心得.md"
)
# noteの心得.mdのパス
NOTE_SAMPLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "public", "サンプル_footer.md"
)


SMALL = "$${{\\footnotesize\\textbf{"
SMALL_END = "}}}$$"


def convert_news_json_to_markdown(news_list: List[Dict]) -> str:
    now = datetime.now()
    header = f"""
🗓️編集者コメント：トレンドから業務に役立つIT技術にフォーカスしてAIが毎日要約してお知らせ

---
"""
    body = ""
    for item in news_list:
        body += f"""
### {item['rank']}. {item['summaryTitle']}

{item['url']}

${SMALL}{item['points'][0]}{SMALL_END}
{SMALL}{item['points'][1]}{SMALL_END}
{SMALL}{item['points'][2]}{SMALL_END}

> {item['summary']}

---
"""
    # [引用元：{item['title']}（{item['users']} USERS）]({item['url']})
    ### [{item['rank']}. {item['summaryTitle']}]({item['url']})

    return header + body


def get_sunday(date: datetime) -> datetime:
    """指定日付の週の日曜日を返す"""
    return date - timedelta(days=date.weekday() + 1) if date.weekday() != 6 else date


def load_titles_from_weekly_txt(txt_path: str) -> set:
    if not os.path.exists(txt_path):
        return set()
    with open(txt_path, encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_titles_to_weekly_txt(txt_path: str, titles: list):
    os.makedirs(os.path.dirname(txt_path), exist_ok=True)
    # 既存のタイトルも考慮して重複しないように追記
    existing = load_titles_from_weekly_txt(txt_path)
    with open(txt_path, "a", encoding="utf-8") as f:
        for title in titles:
            if title not in existing:
                f.write(title + "\n")


def main(publish=True, is_note_write=False):
    entries = fetch_hatena_news_entries()
    is_all = ALL_RANK == RANK_LIMIT

    if not entries:
        print("エントリーが見つかりませんでした。セレクタを確認してください。")
        return

    now = datetime.now()
    # historyディレクトリをsrcの一つ上のディレクトリに指定
    history_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history")
    os.makedirs(history_dir, exist_ok=True)

    # 週ごとのタイトル記録ファイルパスを決定
    sunday = get_sunday(now)
    weekly_txt_dir = os.path.join(
        history_dir, "txt", f"{sunday.year}_{sunday.month:02d}_{sunday.day:02d}"
    )
    os.makedirs(weekly_txt_dir, exist_ok=True)
    weekly_txt_path = os.path.join(weekly_txt_dir, "titles.txt")
    recorded_titles = load_titles_from_weekly_txt(weekly_txt_path)

    history = load_history(weekly_txt_path) if not is_all else []
    # 週ごとの記録済タイトルも除外条件に追加
    top_entries = [
        item
        for item in entries
        if item["title"] not in history and item["title"] not in recorded_titles
    ][:30]

    # top_entriesをトップ7に絞り込む
    top_entries = top_entries[:RANK_LIMIT]

    # top_entriesのタイトルを週ごとのtxtに記録
    if publish and not is_all:
        save_titles_to_weekly_txt(
            weekly_txt_path, [item["title"] for item in top_entries]
        )

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
    for idx, item in enumerate(top_entries):
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
        if item["url"]:
            urlBody = fetch_article_content_from_url(item["url"])
            results = simple(
                topic=f"""{ARTICLE_SUMMARY_PROMPT[0]}

タイトル: {item['title']}
記事: {urlBody}""",
            )
            summary = results[0]
            if summary:
                lines = [line for line in summary.split("\n") if line.strip()]
                entry["summaryTitle"] = lines[0]
                entry["points"] = lines[1:4]
                entry["summary"] = "\n".join(lines[4:]).strip()

        entries_for_json.append(entry)
    save_history_json(json_filename, entries_for_json)
    markdown = convert_news_json_to_markdown(entries_for_json)

    results_eval = simple(
        topic=f"""{ARTICLE_EVALUATION_PROMPT[0]}

【構成は下記のサンプルを意識してください】
{note_sample}

【記事】
{markdown}""",
    )
    linesEval = [line for line in results_eval[0].split("\n")]
    topTitle = TEMPLATE_TITLE if is_all else ""
    markdown = (
        topTitle + linesEval[0] + "\n" + markdown + "\n" + "\n".join(linesEval[1:])
    )

    # markdownをhistory/mdディレクトリに保存
    md_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history", "md")
    os.makedirs(md_dir, exist_ok=True)
    md_filename = os.path.join(
        md_dir,
        f"news_{now.year}_{now.month:02d}_{now.day:02d}_{now.hour:02d}_{now.minute:02d}.md",
    )
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(markdown)

    if is_note_write:
        asyncio.run(post_note(md_filename, headless=False, publish=publish))


if __name__ == "__main__":
    is_debug = sys.gettrace() is not None

    # 第1引数の処理（publish フラグ）
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else None
    if arg == "true":
        publish = True
    else:
        publish = False

    # 第2引数の処理（RANK_LIMIT の上書き）
    if len(sys.argv) > 2:
        try:
            rank_limit_override = int(sys.argv[2])
            if rank_limit_override > 0:
                RANK_LIMIT = rank_limit_override
        except ValueError:
            pass  # 数値以外の場合は無視

    main(publish=publish, is_note_write=not is_debug)
