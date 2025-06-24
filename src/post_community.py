import os
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from utils import simple
import random

load_dotenv()
EMAIL = os.getenv("TWEEt_EMAIL")
USER_NAME = os.getenv("USER_NAME")
TWEET_PASSWORD = os.getenv("TWEET_PASSWORD")

COMMUNITY_URLS = [
    "https://x.com/i/communities/1695273002366300256",
    "https://x.com/i/communities/1742851763986940094",
    "https://x.com/i/communities/1506796313685667840",
    "https://x.com/i/communities/1506803429657944069",
    # "https://x.com/i/communities/1506778440711639042",
    # "https://x.com/i/communities/1771310049350303878",
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
    await page.fill('input[name="password"]', TWEET_PASSWORD)
    await page.click('button:has-text("ログイン")')
    print("パスワードを入力しました。")

    await page.wait_for_timeout(5000)
    print("Twitterへのログインが完了しました。")


async def post_to_communities(page, post_text=None):
    """指定されたテキストを複数のTwitterコミュニティに投稿する"""
    context = page.context
    for i, url in enumerate(COMMUNITY_URLS):
        new_page = await context.new_page()
        try:
            print(f"コミュニティに移動します: {url}")
            await new_page.goto(url)
            await new_page.wait_for_timeout(2000)

            # 「投稿する」ボタンをクリック
            await new_page.click('a[data-testid="SideNav_NewTweet_Button"]')
            await new_page.wait_for_timeout(2000)  # 投稿モーダルが表示されるのを待つ

            # テキストを少し変更して重複を回避
            if post_text:
                emoji = EMOJI_LIST[i % len(EMOJI_LIST)]
                modified_post_text = f"{post_text} {emoji}"
            else:
                modified_post_text = await get_post_text()

            # テキストを入力
            composer_selector = 'div[data-testid="tweetTextarea_0"]'
            await new_page.wait_for_selector(composer_selector, timeout=10000)
            await new_page.fill(composer_selector, modified_post_text)
            # print(f"投稿内容: {modified_post_text}")
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
            wait_seconds = random.randint(1, 6) * 10
            print(f"次の投稿まで {wait_seconds} 秒間待機します...")
            await new_page.wait_for_timeout(wait_seconds * 1000)

        except Exception as e:
            print(f"コミュニティへの投稿中にエラーが発生しました: {url}")
            print(f"エラー詳細: {e}")
            screenshot_path = f"error_community_post_{COMMUNITY_URLS.index(url)}.png"
            await new_page.screenshot(path=screenshot_path)
            print(f"エラーのスクリーンショットを保存しました: {screenshot_path}")
        finally:
            await new_page.close()


async def get_post_text():
    results = simple(
        topic=f"""「フォローよろしくお願いします🙇‍♀️フォローしてくれたら必ずフォロバします！」を同じ意味で40文字以内で微妙に書き直してください。
先頭や文末に～をまとめましたや改行などの情報は不要です。""",
    )
    summary = results[0]
    print(summary)
    post_text = f"{summary}\n#フォロバ100 \n#フォローしてくれた人全員フォローする\n#相互フォロー\n"
    return post_text


async def main(headless=False):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        await login_to_twitter(page)
        await post_to_communities(page)

        print("すべてのコミュニティへの投稿が完了しました。")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
