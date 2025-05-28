import os
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from datetime import datetime
import urllib.parse
from utils import simple
import random

load_dotenv()
EMAIL = os.getenv("NOTE_EMAIL")
PASSWORD = os.getenv("NOTE_PASSWORD")


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
    await new_page.fill('input[name="password"]', PASSWORD)
    await new_page.click('button:has-text("ログイン")')

    # 投稿ボタンが表示されるまで待つ
    await new_page.wait_for_selector('button[data-testid="tweetButton"]', timeout=10000)

    # ボタンをクリック
    await new_page.click('button[data-testid="tweetButton"]')


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
    await page.wait_for_selector(".sc-639f8778-2.djbaCR", timeout=10000)
    await page.wait_for_timeout(2000)  # 追加の待機時間

    image_elements = await page.query_selector_all(".sc-639f8778-2.djbaCR")
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
            await page.wait_for_timeout(20000)
        else:
            print("保存ボタンが見つかりませんでした")
    else:
        print("画像が見つかりませんでした")


async def like_on_note_topic_ai(page, like_count=10, is_suki=True, is_follow=False):
    """
    https://note.com/topic/ai を新しいタブで開き、スキボタンを10個自動で押す
    """
    new_page = await page.context.new_page()
    # await new_page.goto("https://note.com/topic/it")
    await new_page.goto("https://note.com/topic/ai")
    await new_page.wait_for_load_state("load")
    await new_page.wait_for_timeout(2000)  # ページの描画待ち

    if is_suki:
        # 10個の「スキ」ボタンを取得
        like_buttons = await new_page.query_selector_all('button[aria-label="スキ"]')
        random.shuffle(like_buttons)  # ボタンの順番をランダムに
        count = min(like_count, len(like_buttons))
        for i, btn in enumerate(like_buttons[:count]):
            try:
                await btn.click()
                await new_page.wait_for_timeout(
                    random.randint(1, 10) * 500
                )  # 50msの倍数でランダムな待機時間
            except Exception as e:
                print(f"{i+1}個目のスキボタンでエラー: {e}")
        print(f"{count}個のスキを押しました")

    if is_follow:
        try:
            # フォローボタンを取得
            await new_page.goto(
                "https://note.com/search?context=user&q=%E3%83%95%E3%82%A9%E3%83%AD%E3%83%90100&size=10"
            )
            follow_buttons = await new_page.query_selector_all(
                'button.a-button:has-text("フォロー")'
            )
            if follow_buttons:
                # ランダムにlike_count個のフォローボタンを選択してクリック
                random_buttons = random.sample(
                    follow_buttons, min(like_count, len(follow_buttons))
                )
                for i, button in enumerate(random_buttons):
                    await button.click()
                    print(f"{i+1}個目のフォローボタンをクリックしました")
                    await new_page.wait_for_timeout(
                        random.randint(1, 3) * 1000
                    )  # 1-3秒のランダムな待機
            else:
                print("フォローボタンが見つかりませんでした")
        except Exception as e:
            print(f"フォローボタンクリックでエラー: {e}")


async def main(markdown_path, headless=False, publish=False):

    title, body, hashtags = parse_markdown(markdown_path)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()

        page = await context.new_page()

        if True:

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

        # 3. 新規投稿ページへ
        # await page.goto("https://editor.note.com/notes/nb79f5c449093/publish/")
        # # ハッシュタグ入力欄を待つ
        # await page.wait_for_selector('input[placeholder="ハッシュタグを追加する"]')
        # await page.click(
        #     'input[placeholder="ハッシュタグを追加する"]'
        # )  # フォーカスを与える
        # await page.fill('input[placeholder="ハッシュタグを追加する"]', hashtags)
        # print(hashtags)
        # return

        await page.goto("https://note.com/notes/new")

        await page.wait_for_timeout(500)

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
        await page.wait_for_timeout(500)

        await page.keyboard.press("ArrowDown")
        await page.wait_for_timeout(500)

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

        # 6. 下書き保存 or 公開
        if publish:
            await page.wait_for_timeout(500)
            await select_image_add(page)

            print("記事の投稿をします")
            # 「公開に進む」ボタンを押す
            await wait_and_click(page, "公開に進む")

            # ハッシュタグ入力欄を待つ
            await page.wait_for_selector('input[placeholder="ハッシュタグを追加する"]')
            await page.click(
                'input[placeholder="ハッシュタグを追加する"]'
            )  # フォーカスを与える
            await page.fill('input[placeholder="ハッシュタグを追加する"]', hashtags)
            await page.wait_for_timeout(500)

            # 「投稿する」ボタンを押す
            await wait_and_click(page, "投稿する")
            print("記事の投稿が完了しました")

            results = simple(
                topic=f"""記事の内容からtwitterで目を引くような50文字以内の1文のつぶやきにしてください。
先頭や文末に～をまとめましたや改行などの情報は不要です。

記事: {body}""",
            )
            summary = results[0]
            await tweet(page, url, summary)
        else:
            print("記事の下書きをします")
            await wait_and_click(page, "下書き保存")
            print("記事の下書き保存が完了しました")

        await like_on_note_topic_ai(page, is_suki=True, is_follow=True)
        await browser.close()


if __name__ == "__main__":
    import sys

    markdown_path = sys.argv[1] if len(sys.argv) > 1 else MARKDOWN_PATH
    asyncio.run(main(markdown_path))
