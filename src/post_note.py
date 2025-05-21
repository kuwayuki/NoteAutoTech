import os
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()


# Markdownファイルからタイトルと本文を取得
def parse_markdown(file_path):
    with open(file_path, encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]
    title = lines[0].lstrip("#").strip()
    if len(lines) > 2 and lines[-1].startswith("#"):
        hashtags = lines[-1].strip()
        body = "\n".join(lines[1:-1]).strip()
    else:
        hashtags = ""
        body = "\n".join(lines[1:]).strip()
    return title, body, hashtags


async def main(markdown_path="article.md", headless=False, publish=False):
    EMAIL = os.getenv("NOTE_EMAIL")
    PASSWORD = os.getenv("NOTE_PASSWORD")

    title, body, hashtags = parse_markdown(markdown_path)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

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
        await page.goto("https://note.com/notes/new")

        await page.wait_for_timeout(500)

        # 4. タイトル入力
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

        # クリップボードにbodyをコピーしてペースト
        await page.evaluate(f"navigator.clipboard.writeText({body!r})")
        await page.wait_for_timeout(500)
        await page.keyboard.press("Control+V")

        await page.wait_for_timeout(500)

        # 6. 下書き保存 or 公開
        if publish:
            # 「公開に進む」ボタンを押す
            await page.click("text=公開に進む")
            await page.wait_for_timeout(1000)

            # ハッシュタグ入力欄を待つ
            await page.wait_for_selector('input[placeholder="ハッシュタグを追加する"]')
            await page.click(
                'input[placeholder="ハッシュタグを追加する"]'
            )  # フォーカスを与える
            await page.evaluate(f"navigator.clipboard.writeText({hashtags!r})")
            await page.wait_for_timeout(500)
            await page.keyboard.press("Control+V")
            await page.wait_for_timeout(500)

            # 「投稿する」ボタンを押す
            await page.click('button:has-text("投稿する")')
            print("記事の投稿が完了しました")
        else:
            await page.click("text=下書き保存")
            print("記事の下書き保存が完了しました")

        # await browser.close()


if __name__ == "__main__":
    import sys

    markdown_path = sys.argv[1] if len(sys.argv) > 1 else "article.md"
    asyncio.run(main(markdown_path))
