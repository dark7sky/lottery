from __future__ import annotations

import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from playwright.sync_api import Page, sync_playwright

from .models import (
    MAX_GAMES_PER_PURCHASE,
    MIN_GAMES_PER_PURCHASE,
    STATUS_FAILURE,
    STATUS_INSUFFICIENT_BALANCE,
    STATUS_SUCCESS,
    PurchaseAttempt,
    RuntimeConfig,
)


def _send_telegram_message(config: RuntimeConfig, message: str) -> None:
    if config.telegram is None:
        return

    payload = urlencode(
        {"chat_id": config.telegram.chat_id, "text": message}
    ).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{config.telegram.bot_token}/sendMessage",
        data=payload,
        method="POST",
    )

    with urlopen(request, timeout=10) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(f"Telegram 전송 실패: {result}")


def _safe_send_telegram_message(config: RuntimeConfig, message: str) -> str | None:
    if config.telegram is None:
        return None

    try:
        _send_telegram_message(config, message)
    except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
        return str(exc)
    return None


def _normalize_ticket_lines(message: str) -> list[str]:
    lines: list[str] = []
    for raw_line in message.splitlines():
        cleaned = " ".join(raw_line.split())
        if cleaned:
            lines.append(cleaned)

    number_lines = [
        line
        for line in lines
        if len(re.findall(r"\d{1,2}", line)) >= 6
    ]
    if number_lines:
        return number_lines

    numbers = re.findall(r"\d{1,2}", message)
    if len(numbers) >= 6:
        return [" ".join(numbers[index:index + 6]) for index in range(0, len(numbers), 6)]
    return []


def _get_purchase_result(page: Page, timeout_ms: int = 10000) -> tuple[str, bool]:
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


def _build_notification_message(attempt: PurchaseAttempt) -> str:
    trigger_label = "수동 실행" if attempt.trigger == "manual" else "예약 실행"
    lines = [f"[동행복권] {trigger_label}", attempt.message]
    if attempt.balance is not None:
        lines.append(f"잔액: {attempt.balance:,}원")
    if attempt.ticket_lines:
        lines.append("")
        lines.extend(attempt.ticket_lines)
    if attempt.error and attempt.error not in attempt.message:
        lines.append("")
        lines.append(f"오류: {attempt.error}")
    return "\n".join(lines)


def run_purchase(
    config: RuntimeConfig,
    trigger: str,
    request_id: str,
    games_requested: int | None = None,
) -> PurchaseAttempt:
    games = games_requested or config.games_per_purchase
    if not MIN_GAMES_PER_PURCHASE <= games <= MAX_GAMES_PER_PURCHASE:
        raise ValueError(
            f"구매 게임 수는 {MIN_GAMES_PER_PURCHASE}에서 "
            f"{MAX_GAMES_PER_PURCHASE} 사이여야 합니다."
        )

    attempt = PurchaseAttempt(
        request_id=request_id,
        trigger=trigger,
        status=STATUS_FAILURE,
        message="구매를 시작하지 못했습니다.",
        games_requested=games,
    )

    try:
        launch_kwargs: dict = {"headless": config.browser.headless}
        if config.browser.executable_path:
            launch_kwargs["executable_path"] = config.browser.executable_path
        if config.browser.args:
            launch_kwargs["args"] = list(config.browser.args)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_kwargs)
            context = browser.new_context(**playwright.devices[config.browser.device_name])
            page = context.new_page()
            try:
                page.goto("https://www.dhlottery.co.kr/")
                page.get_by_role("button", name="로그인").click()
                page.get_by_role("textbox", name="아이디").click()
                page.get_by_role("textbox", name="아이디").fill(config.credentials.user_id)
                page.get_by_role("textbox", name="비밀번호").click()
                page.get_by_role("textbox", name="비밀번호").fill(config.credentials.password)
                page.locator("#btnLogin").click()
                page.get_by_role("button", name="로또6/45").click()
                money_text = page.locator(".myAcct-money > span").first.inner_text().strip()
                if "원" not in money_text:
                    raise ValueError(f"로그인 실패? 잔액={money_text}")

                attempt.balance = int(money_text.replace(",", "").replace("원", ""))
                if attempt.balance < games * 1000:
                    attempt.status = STATUS_INSUFFICIENT_BALANCE
                    attempt.message = (
                        f"잔액이 부족합니다. 현재 잔액: {attempt.balance:,}원, "
                        f"필요 금액: {games * 1000:,}원"
                    )
                else:
                    for _ in range(games):
                        page.get_by_role("button", name="자동 1매 추가").click()

                    page.get_by_role("button", name="구매하기").click()
                    page.get_by_role("button", name="확인").click()
                    raw_message, is_success = _get_purchase_result(
                        page, timeout_ms=config.purchase_timeout_ms
                    )
                    attempt.raw_message = raw_message
                    attempt.ticket_lines = _normalize_ticket_lines(raw_message)

                    if is_success:
                        attempt.status = STATUS_SUCCESS
                        attempt.message = raw_message
                    else:
                        attempt.status = STATUS_FAILURE
                        attempt.message = f"로또 구매 실패: {raw_message}"
            finally:
                context.close()
                browser.close()
    except Exception as exc:
        attempt.status = STATUS_FAILURE
        attempt.error = str(exc)
        attempt.message = f"로또 구매 중 오류 발생: {exc}"
    finally:
        attempt.finish()

    telegram_error = _safe_send_telegram_message(config, _build_notification_message(attempt))
    if telegram_error:
        attempt.error = (
            f"{attempt.error} | Telegram: {telegram_error}"
            if attempt.error
            else f"Telegram: {telegram_error}"
        )

    return attempt
