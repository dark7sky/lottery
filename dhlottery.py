import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from playwright.sync_api import Page, Playwright, sync_playwright
from dotenv import load_dotenv

def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} 환경변수가 설정되지 않았습니다.")
    return value

def send_telegram_message(message: str) -> None:
    bot_token = require_env("TELEGRAM_BOT_TOKEN")
    chat_id = require_env("TELEGRAM_CHAT_ID")

    payload = urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=payload,
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok"):
            print(f"Telegram 전송 실패: {result}")
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"Telegram 전송 실패: {exc}")

def get_purchase_result(page: Page, timeout_ms: int = 10000) -> tuple[str, bool]:
    success_locator = page.locator("ticket-num-box").first
    failure_locator = page.locator(
        'xpath=//*[@id="popupLayerConfirm"]/div/div[2]/div[2]/p[1]'
    ).first
    deadline = time.monotonic() + (timeout_ms / 1000)

    while time.monotonic() < deadline:
        if success_locator.count() > 0 and success_locator.is_visible():
            return success_locator.inner_text().strip(), True
        if failure_locator.count() > 0 and failure_locator.is_visible():
            return failure_locator.inner_text().strip(), False
        page.wait_for_timeout(250)

    raise TimeoutError("구매 결과 메시지를 확인하지 못했습니다.")

def run(playwright: Playwright, games: int = 5) -> None:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(**playwright.devices["Galaxy S24"])
    page = context.new_page()
    try:
        page.goto("https://www.dhlottery.co.kr/")
        page.get_by_role("button", name="로그인").click()
        page.get_by_role("textbox", name="아이디").click()
        page.get_by_role("textbox", name="아이디").fill(require_env("DHLOTTERY_ID"))
        page.get_by_role("textbox", name="비밀번호").click()
        page.get_by_role("textbox", name="비밀번호").fill(require_env("DHLOTTERY_PW"))
        page.locator("#btnLogin").click()
        page.get_by_role("button", name="로또6/45").click()
        money = page.locator(".myAcct-money > span").first.inner_text().strip()
        if "원" not in money:
            raise ValueError(f"로그인 실패? 잔액={money}")

        money = int(money.replace(",", "").replace("원", ""))
        print(f"잔액: {money:,}원")
        if money < games * 1000:
            low_balance_message = (
                f"잔액이 부족합니다. 충전을 진행해주세요. 현재 잔액: {money:,}원"
            )
            print(f"잔액이 부족합니다. {games}게임 구매에 {games * 1000:,}원이 필요합니다.")
            send_telegram_message(low_balance_message)
            return

        for _ in range(games):
            page.get_by_role("button", name="자동 1매 추가").click()

        page.get_by_role("button", name="구매하기").click()
        page.get_by_role("button", name="확인").click()
        msg, is_success = get_purchase_result(page)
        if not is_success:
            msg = f"로또 구매 실패: {msg}"

        print(msg)
        send_telegram_message(msg)
        if not is_success:
            raise RuntimeError(msg)
    finally:
        context.close()
        browser.close()


def main():
    # .env 파일 로드
    load_dotenv()
    require_env("DHLOTTERY_ID")
    require_env("DHLOTTERY_PW")
    require_env("TELEGRAM_BOT_TOKEN")
    require_env("TELEGRAM_CHAT_ID")
    with sync_playwright() as playwright:
        run(playwright, games=5)

if __name__ == "__main__":
    try: main()
    except Exception as exc:
        print(f"오류 발생: {exc}")
        send_telegram_message(f"로또 구매 중 오류 발생: {exc}")
