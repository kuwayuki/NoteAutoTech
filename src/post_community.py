import os
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from utils import simple
import random

load_dotenv()
EMAIL = os.getenv("NOTE_EMAIL")
PASSWORD = os.getenv("NOTE_PASSWORD")
USER_NAME = os.getenv("USER_NAME")

COMMUNITY_URLS = [
    "https://x.com/i/communities/1695273002366300256",  # 万垢を目指す会
    "https://x.com/i/communities/1742851763986940094",  # 相互フォローしようの会
    "https://x.com/i/communities/1634787609515036673",  # 相互の会
    "https://x.com/i/communities/1506796313685667840",  # 相互フォロー募集
    "https://x.com/i/communities/1506803429657944069",  # フォロバ100%コミュニティ
    "https://x.com/i/communities/1506778440711639042",  # フォロバ100の界隈
    # "https://x.com/i/communities/1771310049350303878", # 相互フォロー募集
]

EMOJI_LIST = ["✨", "🚀", "🎉", "💪", "🔥", "✅", "😊", "💡", "🌟", "🙌", "💯", "👍"]


async def login_to_twitter(page):
    """Twitterにログインする"""
    print("Twitterにログインします...")
    await page.goto("https://x.com/login", wait_until="networkidle")

    # メールアドレス入力
    await page.wait_for_selector('input[name="text"]', timeout=10000)
    await page.fill('input[name="text"]', EMAIL)
    await page.click('button:has-text("次へ")')
    print("メールアドレスを入力しました。")

    # ユーザー名/電話番号の確認画面が表示される場合がある
    try:
        username_input_selector = 'input[data-testid="ocfEnterTextTextInput"]'
        await page.wait_for_selector(username_input_selector, timeout=5000)
        await page.fill(username_input_selector, USER_NAME)
        await page.click('button:has-text("次へ")')
        print("ユーザー名を入力しました。")
    except Exception:
        print("ユーザー名の入力はスキップされました。")

    # パスワード入力
    await page.wait_for_selector('input[name="password"]', timeout=10000)
    await page.fill('input[name="password"]', PASSWORD)
    await page.click('button:has-text("ログイン")')
    print("パスワードを入力しました。")

    await page.wait_for_timeout(5000)
    print("Twitterへのログインが完了しました。")


async def post_to_single_community(context, url, post_text, index):
    """一つのコミュニティに投稿するタスク"""
    new_page = await context.new_page()
    try:
        # 投稿タイミングを少しずらすためのランダムな待機
        wait_seconds = random.randint(5, 60)
        print(
            f"タブ {index + 1} ({url.split('/')[-1]}): {wait_seconds}秒後に処理を開始します。"
        )
        await new_page.wait_for_timeout(wait_seconds * 1000)

        print(f"コミュニティに移動します: {url}")
        await new_page.goto(url)
        await new_page.wait_for_timeout(2000)

        # 「投稿する」ボタンをクリック
        await new_page.click('a[data-testid="SideNav_NewTweet_Button"]')
        await new_page.wait_for_timeout(2000)  # 投稿モーダルが表示されるのを待つ

        # テキストを少し変更して重複を回避
        emoji = EMOJI_LIST[index % len(EMOJI_LIST)]
        modified_post_text = f"{post_text} {emoji}"

        # テキストを入力
        composer_selector = 'div[data-testid="tweetTextarea_0"]'
        await new_page.wait_for_selector(composer_selector, timeout=10000)
        await new_page.fill(composer_selector, modified_post_text)
        print(f"投稿内容: {modified_post_text}")
        await new_page.wait_for_timeout(500)

        # 投稿ボタンをクリック
        post_button_selector = 'button[data-testid="tweetButton"]'
        await new_page.wait_for_selector(post_button_selector)

        # ボタンが有効になるまで少し待つ
        await new_page.wait_for_function(
            f"document.querySelector('{post_button_selector}').disabled === false"
        )

        await new_page.click(post_button_selector)
        print(f"コミュニティに投稿しました: {url}")
        await new_page.wait_for_timeout(3000)  # 投稿が完了するのを待つ

    except Exception as e:
        print(f"コミュニティへの投稿中にエラーが発生しました: {url}")
        print(f"エラー詳細: {e}")
        screenshot_path = f"error_community_post_{index}.png"
        await new_page.screenshot(path=screenshot_path)
        print(f"エラーのスクリーンショットを保存しました: {screenshot_path}")
    finally:
        await new_page.close()


async def post_to_communities(page, post_text):
    """指定されたテキストを複数のTwitterコミュニティに並行して投稿する"""
    context = page.context
    tasks = []
    for i, url in enumerate(COMMUNITY_URLS):
        task = asyncio.create_task(post_to_single_community(context, url, post_text, i))
        tasks.append(task)
    await asyncio.gather(*tasks)


async def main(headless=False):
    # --- 投稿するメッセージをここに設定 ---
    # noteのURLなど、投稿したい内容を記載
    results = simple(
        topic=f"""「フォローお願いします！🙇‍♀️フォローしてくれたら必ずフォロバします！」の文を同じ意味の文に書き直してください。絶対に30文字以内です。
先頭や文末に～をまとめましたや改行などの情報は不要です。""",
    )
    summary = results[0]
    post_text = f"{summary}\n#フォロバ100 \n#フォローしてくれた人全員フォローする\n#相互フォロー\n"
    print(post_text)
    # ---

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        await login_to_twitter(page)
        await post_to_communities(page, post_text)

        print("すべてのコミュニティへの投稿が完了しました。")
        await browser.close()


if __name__ == "__main__":
    # headフルモードで実行したい場合は False に変更
    # 例: asyncio.run(main(headless=False))
    asyncio.run(main())
