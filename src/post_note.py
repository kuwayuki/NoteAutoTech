import os
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from datetime import datetime
import urllib.parse
from utils import simple, question
import random
import sys
import re
from screeninfo import get_monitors

load_dotenv()
EMAIL = os.getenv("NOTE_EMAIL")
PASSWORD = os.getenv("NOTE_PASSWORD")
TWEET_PASSWORD = os.getenv("TWEET_PASSWORD")


# Markdownファイルからタイトルと本文を取得
def parse_markdown(file_path):
    with open(file_path, encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]
    title = lines[0].lstrip("#").strip()

    # now = datetime.now()
    # today = f"{now.year}/{now.month}/{now.day} {now.hour}:00"
    # title = f"【{today} 最新】毎日たった 5 分で技術トレンドを掴む！"
    if len(lines) > 2 and lines[-1].startswith("#"):
        hashtags = lines[-1].strip()
        body = "\n".join(lines[1:-1]).strip()
    else:
        hashtags = ""
        body = "\n".join(lines[1:]).strip()
    return title, body, hashtags


MARKDOWN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "history", "md", "article.md"
)


async def tweet(page, url, title):
    # 1. URL取得
    full_url = url
    note_url = full_url.split("/edit/")[0].replace(
        "editor.note.com/notes/", "note.com/lush_chimp5185/n/"
    )

    # エンコード
    title_encoded = urllib.parse.quote(title.split("】")[-1].strip())
    note_url_encoded = urllib.parse.quote(note_url)

    # Twitter投稿用URL
    twitter_url = f"https://x.com/intent/post?text={title_encoded}&related=note_PR&url={note_url_encoded}"

    # 新しいタブで開く
    new_page = await page.context.new_page()
    await new_page.goto(twitter_url)
    await new_page.wait_for_load_state("load")

    # ログインボタンが出てくるまで待機
    await new_page.wait_for_selector('button:has-text("ログイン")', timeout=10000)
    await new_page.click('button:has-text("ログイン")')

    # メールアドレス入力
    await new_page.wait_for_selector('input[name="text"]', timeout=10000)
    await new_page.fill('input[name="text"]', EMAIL)
    await new_page.click('button:has-text("次へ")')

    await new_page.wait_for_selector(
        'input[data-testid="ocfEnterTextTextInput"]', timeout=10000
    )
    await new_page.fill(
        'input[data-testid="ocfEnterTextTextInput"]', os.getenv("USER_NAME")
    )
    await new_page.click('button:has-text("次へ")')

    # パスワード入力
    await new_page.wait_for_selector('input[name="password"]', timeout=10000)
    await new_page.fill('input[name="password"]', TWEET_PASSWORD)
    await new_page.click('button:has-text("ログイン")')

    # 投稿ボタンが表示されるまで待つ
    await new_page.wait_for_selector('button[data-testid="tweetButton"]', timeout=10000)

    # ボタンをクリック
    await new_page.click('button[data-testid="tweetButton"]')


async def login(page, context):

    # 1. note.comログインページへ
    await page.goto("https://note.com/login")

    await page.wait_for_timeout(500)

    # 2. ログイン
    await page.fill("#email", EMAIL)
    await page.fill("#password", PASSWORD)

    await page.wait_for_timeout(500)
    await page.click('button:has-text("ログイン")')
    await page.wait_for_load_state("networkidle")

    # ログイン後、reCAPTCHAが出ているかチェック
    await page.wait_for_timeout(1000)

    recaptcha_present = await page.query_selector(
        'iframe[src*="recaptcha"]'
    ) or await page.query_selector("text=私はロボットではありません")

    if recaptcha_present:
        print("reCAPTCHAが表示されています。Googleログインで再認証します。")
        # Googleログインボタンをクリック
        await page.click('button[aria-label="Google"]')
        # Googleログイン画面の新しいページ（タブ）を待つ
        google_page = await context.wait_for_event("page")
        await google_page.wait_for_load_state()
        # メールアドレス入力
        await google_page.wait_for_selector("#identifierId")
        await google_page.fill("#identifierId", EMAIL)
        await google_page.click('button:has-text("次へ")')
        await google_page.wait_for_timeout(1000)
        # パスワード入力
        await google_page.wait_for_selector('input[type="password"]')
        await google_page.fill('input[type="password"]', PASSWORD)
        await google_page.click('button:has-text("次へ")')
        await google_page.wait_for_load_state("networkidle")
        print("Googleログイン完了")
        # 元のページに戻る
        await page.bring_to_front()


async def wait_and_click(page, button_text, timeout=10000):
    selector = f'button:has-text("{button_text}")'
    await page.wait_for_selector(selector, timeout=timeout)
    await page.click(selector)
    await page.wait_for_timeout(1000)


async def select_image_add(page):
    # 画像追加ボタンをクリック
    await page.click('button[aria-label="画像を追加"]')
    await page.wait_for_timeout(500)

    # 「記事にあう画像を選ぶ」をクリック
    await page.click('button:has-text("記事にあう画像を選ぶ")')
    await page.wait_for_timeout(1000)

    # 画像グリッドからランダムに1つ選択
    # 画像が表示されるまで待機
    IMAGE_GRID_SELECTOR = 'div[role="button"]'  # これならクラス名が変わってもOK
    await page.wait_for_selector(IMAGE_GRID_SELECTOR, timeout=10000)
    await page.wait_for_timeout(2000)

    image_elements = await page.query_selector_all(IMAGE_GRID_SELECTOR)
    if image_elements:
        # ランダムに1つの画像を選択
        random_image = random.choice(image_elements)
        await random_image.click()
        await page.wait_for_timeout(1000)

        # 「この画像を挿入」ボタンをクリック
        await page.click('button:has-text("この画像を挿入")')
        await page.wait_for_timeout(3000)

        # モーダル内の保存ボタンを明示的に取得してクリック
        modal = await page.wait_for_selector('div[role="dialog"]', timeout=5000)
        save_button = await modal.query_selector('button:has-text("保存")')
        if save_button:
            await save_button.scroll_into_view_if_needed()
            await save_button.click()
            await page.wait_for_timeout(6000)
        else:
            print("保存ボタンが見つかりませんでした")
    else:
        print("画像が見つかりませんでした")


async def click_random_buttons(
    page,
    url,
    selector,
    count,
    action_name,
    min_wait=1,
    max_wait=10,
    wait_multiplier=500,
):
    await page.goto(url)
    await page.wait_for_load_state("load")
    await page.wait_for_timeout(2000)  # ページの描画待ち

    clicked = 0
    roop_count = 0

    while clicked < count:
        buttons = []
        for btn in await page.query_selector_all(selector):
            try:
                text = await btn.inner_text()
                aria_label = (await btn.get_attribute("aria-label")) or ""
                if "中" not in text and "取り消す" not in aria_label:
                    buttons.append(btn)
            except Exception as e:
                print(f"ボタン確認中にエラー: {e}")

        random.shuffle(buttons)
        found_clickable = False

        for btn in buttons:

            try:
                text = await btn.inner_text()
                if "中" in text:
                    print(
                        f"スキップ: {clicked+1}個目の{action_name}ボタン（「中」含む）"
                    )
                    continue
                await btn.click()
                await page.wait_for_timeout(
                    random.randint(min_wait, max_wait) * wait_multiplier
                )
                print(f"{clicked+1}個目の{action_name}ボタンをクリックしました")
                clicked += 1
                found_clickable = True
                if clicked >= count:
                    break
            except Exception as e:
                print(f"{clicked+1}個目の{action_name}ボタンでエラー: {e}")

        if not found_clickable:
            print(f"再取得します")
            # スクロールして再取得
            page_height = await page.evaluate("() => document.body.scrollHeight")
            scroll_to = random.randint(0, int(page_height * 0.8))
            await page.evaluate(f"window.scrollTo(0, {scroll_to})")
            await page.wait_for_timeout(1000)
            roop_count += 1
            if roop_count > 10:
                break
            # ループ継続
        else:
            await page.wait_for_timeout(500)

    print(f"{clicked}個の{action_name}を押しました")


async def like_on_note_topic_ai(page, is_suki=True, is_follow=False):
    tasks = []
    search_word = random_search_word()
    encoded_search = urllib.parse.quote(search_word)

    if is_suki:
        new_page_suki = await page.context.new_page()
        tasks.append(
            asyncio.create_task(
                click_random_buttons(
                    new_page_suki,
                    # "https://note.com/",
                    f"https://note.com/search?q={encoded_search}&context=note&mode=search",
                    'button[aria-label="スキ"]',
                    23,
                    "スキ",
                )
            )
        )

    if is_follow:
        new_page_follow = await page.context.new_page()
        tasks.append(
            asyncio.create_task(
                click_random_buttons(
                    new_page_follow,
                    # "https://note.com/search?context=user&q=IT&size=10",
                    f"https://note.com/search?context=user&q={encoded_search}&size=10",
                    'button.a-button:has-text("フォロー")',
                    13,
                    "フォロー",
                )
            )
        )

    if tasks:
        await asyncio.gather(*tasks)


async def main(markdown_path, headless=False, publish=True):

    title, body, hashtags = parse_markdown(markdown_path)

    async with async_playwright() as p:
        # browser = await p.chromium.launch(headless=headless, args=["--start-maximized"])
        # primary_monitor = get_monitors()[0]  # プライマリモニターを取得
        # context = await browser.new_context(
        #     viewport={"width": primary_monitor.width, "height": primary_monitor.height}
        # )

        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        await login(page, context)
        # await like_on_note_topic_ai(page, is_suki=True, is_follow=False)
        # return

        await page.goto("https://note.com/notes/new")

        await page.wait_for_timeout(500)

        # 6. 下書き保存 or 公開
        if publish:
            await select_image_add(page)

        # 4. タイトル入力
        url = page.url
        print(url)

        await page.wait_for_selector('textarea[placeholder="記事タイトル"]')
        await page.fill('textarea[placeholder="記事タイトル"]', title)

        await page.wait_for_timeout(500)

        # 5. 本文入力（クリップボード経由でペースト）
        await page.wait_for_selector("div.ProseMirror")
        await page.click("div.ProseMirror")  # フォーカスを明示的に与える

        await page.wait_for_timeout(500)
        # メニューボタンをクリック
        await page.wait_for_selector('button[aria-label="メニューを開く"]')
        await page.click('button[aria-label="メニューを開く"]')
        await page.wait_for_timeout(500)

        # 目次ボタンをクリック
        await page.wait_for_selector("#toc-setting")
        await page.click("#toc-setting")
        await page.wait_for_timeout(1000)

        await page.keyboard.press("ArrowDown")
        await page.wait_for_timeout(1000)

        # (2) paste イベントを発火させて本文を挿入
        await page.evaluate(
            """(text) => {
            const editor = document.querySelector("div.ProseMirror");
            if (!editor) {
                console.error("ProseMirror エディタ要素が見つかりません");
                return;
            }
            editor.focus();
            // DataTransfer を使って clipboardData を作成
            const dt = new DataTransfer();
            dt.setData("text/plain", text);
            // paste イベントを生成
            const pasteEvent = new ClipboardEvent("paste", {
                clipboardData: dt,
                bubbles: true,
                cancelable: true
            });
            // エディタ要素に dispatch
            editor.dispatchEvent(pasteEvent);
            }""",
            body,
        )

        await page.wait_for_timeout(1000)

        # 貼り付けられたリンクを全て取得
        link_elements = await page.query_selector_all('div.ProseMirror a[href^="http"]')

        for link in link_elements:
            # 親要素（段落ブロック）を取得
            parent = await link.evaluate_handle("el => el.closest('p, div, li')")

            # 親要素が取得できたらクリック
            if parent:
                await parent.click()
                await page.wait_for_timeout(300)

                # 行末に移動（Endキー）
                await page.keyboard.press("End")
                await page.wait_for_timeout(200)

                # Enterキー → Deleteキー
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(200)
                await page.keyboard.press("Delete")
                await page.wait_for_timeout(300)

        # 6. 下書き保存 or 公開
        if publish:
            await page.wait_for_timeout(500)

            print("記事の投稿をします")
            # 「公開に進む」ボタンを押す
            await wait_and_click(page, "公開に進む")

            # ハッシュタグ入力欄を待つ
            await page.wait_for_selector('input[placeholder="ハッシュタグを追加する"]')
            await page.click(
                'input[placeholder="ハッシュタグを追加する"]'
            )  # フォーカスを与える
            for tag in hashtags.split():
                if tag:
                    await page.fill('input[placeholder="ハッシュタグを追加する"]', tag)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(200)

            # 「投稿する」ボタンを押す
            await wait_and_click(page, "投稿する")
            print("記事の投稿が完了しました")

            results = simple(
                topic=f"""記事の内容からtwitterで目を引くようにトレンドに沿って刺激的な80文字以内の1文のつぶやきにしてください。
先頭や文末に～をまとめましたや改行などの情報は不要です。

記事: {body}""",
            )
            summary = results[0]
            # 一旦コメントアウト
            await tweet(page, url, summary)

            await like_on_note_topic_ai(page, is_suki=True, is_follow=True)
        else:
            print("記事の下書きをします")
            await wait_and_click(page, "下書き保存")
            print("記事の下書き保存が完了しました")

        await browser.close()


def random_search_word():
    try:
        search_word = question(
            "IT関連において、ユーザーを探すためのキーワードを配列のみ教えてください。回答例：['IT', 'React', 'フロントエンド', ...]"
        )

        # シングルクォーテーションで囲まれた文字列を抽出
        pattern = r"'([^']*)'"
        search_words = re.findall(pattern, search_word)
        search_word = random.choice(search_words)
    except Exception:
        search_word = "IT"
    print(f"Selected search word: {search_word}")

    return search_word


if __name__ == "__main__":
    markdown_path = sys.argv[1] if len(sys.argv) > 1 else MARKDOWN_PATH
    asyncio.run(main(markdown_path))
