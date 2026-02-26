import base64
import asyncio
import os
import re
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError
from server.config import settings
from server.agent.models import Step
from server.agent.safety import SafeModeBlocked

BLOCKED_KEYWORDS = (
    "checkout",
    "payment",
    "pay",
    "enroll",
    "subscribe",
    "purchase",
    "buy",
)

SEARCH_INPUT_SELECTORS = [
    "input[type='search']",
    "input[placeholder*='search' i]",
    "input[name*='search' i]",
    "input[id*='search' i]",
    "input[aria-label*='search' i]",
    "input[placeholder*='query' i]",
    "input[name*='query' i]",
]

SEARCH_BUTTON_SELECTORS = [
    "button[aria-label*='search' i]",
    "button[title*='search' i]",
    "button[type='submit']",
    "button svg[aria-label*='search' i]",
]

class PlaywrightController:
    def __init__(self, persistent: bool = True, user_data_dir: str | None = None) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._persistent = persistent
        self._user_data_dir = user_data_dir

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        await self._loop.run_in_executor(self._executor, self._start_sync)

    async def stop(self) -> None:
        if self._loop:
            await self._loop.run_in_executor(self._executor, self._stop_sync)
        self._executor.shutdown(wait=True, cancel_futures=True)

    async def screenshot_base64(self) -> str | None:
        if not self._loop:
            return None
        return await self._loop.run_in_executor(self._executor, self._screenshot_sync)

    async def get_current_url(self) -> str | None:
        """Get current page URL for frame source display."""
        if not self._loop:
            return None
        return await self._loop.run_in_executor(self._executor, self._get_current_url_sync)

    async def perform_action(self, step: Step) -> None:
        if not self._loop:
            raise RuntimeError("Browser page is not initialized")
        await self._loop.run_in_executor(self._executor, self._perform_action_sync, step)

    async def run_in_executor(self, func, *args):
        if not self._loop:
            raise RuntimeError("Browser page is not initialized")
        return await self._loop.run_in_executor(self._executor, func, *args)

    def _start_sync(self) -> None:
        self._playwright = sync_playwright().start()
        if self._persistent:
            user_data_dir = self._user_data_dir or settings.user_data_dir
            user_data_dir = os.path.abspath(user_data_dir)
            os.makedirs(user_data_dir, exist_ok=True)
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=settings.playwright_headless,
                slow_mo=settings.slow_mo_ms,
            )
            if not self._context:
                raise RuntimeError("Browser context failed to launch")
            pages = self._context.pages
            self._page = pages[0] if pages else self._context.new_page()
        else:
            self._browser = self._playwright.chromium.launch(
                headless=settings.playwright_headless,
                slow_mo=settings.slow_mo_ms,
            )
            self._context = self._browser.new_context()
            self._page = self._context.new_page()

        if not self._page:
            raise RuntimeError("Failed to create page")
        self._page.set_default_timeout(settings.browser_timeout)

    def _stop_sync(self) -> None:
        try:
            if self._page:
                self._page.close()
        except Exception:
            pass
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass

    def _screenshot_sync(self) -> str | None:
        if not self._page:
            return None
        data = self._page.screenshot(type="png")
        return base64.b64encode(data).decode("utf-8")

    def _get_current_url_sync(self) -> str | None:
        if not self._page:
            return None
        return self._page.url or None

    def _highlight(self, selector: str) -> None:
        if not self._page:
            return
        try:
            # Attempt to highlight the element with a red border and yellow background
            # We use evaluate to inject style. This might not persist if the page navigates immediately,
            # but usually provides a visual cue.
            self._page.evaluate(
                f"""(selector) => {{
                    const el = document.querySelector(selector);
                    if (el) {{
                        el.style.border = '3px solid red';
                        el.style.backgroundColor = 'rgba(255, 255, 0, 0.3)';
                        el.style.transition = 'all 0.3s';
                        el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                    }}
                }}""",
                selector
            )
            # Short wait to let the user see the highlight in the stream
            self._page.wait_for_timeout(500)
        except Exception:
            # Highlighting is best-effort; don't fail the step if it fails
            pass

    def _perform_action_sync(self, step: Step) -> None:
        if not self._page:
            raise RuntimeError("Browser page is not initialized")

        action = step.action
        if step.selector:
            step.selector = _normalize_selector(step.selector)
        if self._is_blocked_action(step):
            raise SafeModeBlocked("Blocked by safe mode: login/payment/enrollment action detected")
        if action == "navigate":
            if not step.url:
                raise ValueError("navigate requires url")
            target_url = _sanitize_url(step.url)
            self._page.goto(target_url, wait_until="domcontentloaded")
            return
        if action == "click":
            if not step.selector:
                raise ValueError("click requires selector")
            if self._is_login_selector(step.selector):
                return
            self._highlight(step.selector)
            try:
                self._page.click(step.selector)
            except PlaywrightTimeoutError:
                if self._is_login_selector(step.selector):
                    return
                if step.selector.strip() == "a h3":
                    try:
                        self._page.locator("a:has(h3)").first.click(timeout=settings.browser_timeout)
                        return
                    except PlaywrightTimeoutError:
                        try:
                            self._page.get_by_role("link").first.click(timeout=settings.browser_timeout)
                            return
                        except PlaywrightTimeoutError:
                            try:
                                self._page.locator("a[href]").first.click(timeout=settings.browser_timeout)
                                return
                            except PlaywrightTimeoutError:
                                pass
                if step.selector.startswith("text="):
                    text_value = step.selector.split("=", 1)[1].strip().strip("\"").strip("'")
                    try:
                        self._page.get_by_text(text_value, exact=False).click(timeout=settings.browser_timeout)
                        return
                    except PlaywrightTimeoutError:
                        try:
                            self._page.get_by_role("button", name=text_value).first.click(timeout=settings.browser_timeout)
                            return
                        except PlaywrightTimeoutError:
                            try:
                                self._page.get_by_role("link", name=text_value).first.click(timeout=settings.browser_timeout)
                                return
                            except PlaywrightTimeoutError:
                                try:
                                    safe = text_value.replace("'", "\\'")
                                    self._page.locator(f"a:has-text('{safe}')").first.click(timeout=settings.browser_timeout)
                                    return
                                except PlaywrightTimeoutError:
                                    try:
                                        self._page.locator(f"button:has-text('{safe}')").first.click(timeout=settings.browser_timeout)
                                        return
                                    except PlaywrightTimeoutError:
                                        pass
                if self._is_search_selector(step.selector):
                    try:
                        self._click_first_available(SEARCH_BUTTON_SELECTORS)
                    except PlaywrightTimeoutError:
                        selector = self._first_available(SEARCH_INPUT_SELECTORS)
                        if selector:
                            self._page.press(selector, "Enter")
                        else:
                            raise
                else:
                    raise
            return
        if action == "type":
            if not step.selector:
                raise ValueError("type requires selector")
            self._highlight(step.selector)
            try:
                self._page.fill(step.selector, step.text or "")
            except PlaywrightTimeoutError:
                if self._is_search_selector(step.selector):
                    try:
                        self._fill_first_available(SEARCH_INPUT_SELECTORS, step.text or "")
                    except PlaywrightTimeoutError:
                        self._click_first_available(SEARCH_BUTTON_SELECTORS)
                        self._page.wait_for_timeout(400)
                        self._fill_first_available(SEARCH_INPUT_SELECTORS, step.text or "")
                else:
                    raise
            return
        if action == "press":
            if not step.selector:
                raise ValueError("press requires selector")
            key = step.key or "Enter"
            self._highlight(step.selector)
            try:
                self._page.press(step.selector, key)
            except PlaywrightTimeoutError:
                if self._is_search_selector(step.selector):
                    selector = self._first_available(SEARCH_INPUT_SELECTORS)
                    if selector:
                        self._page.press(selector, key)
                        return
                    self._click_first_available(SEARCH_BUTTON_SELECTORS)
                    self._page.wait_for_timeout(400)
                    selector = self._first_available(SEARCH_INPUT_SELECTORS)
                    if selector:
                        self._page.press(selector, key)
                    else:
                        raise
                else:
                    raise
            return
        if action == "scroll":
            amount = step.amount if step.amount is not None else 800
            self._page.mouse.wheel(0, amount)
            return
        if action == "wait":
            ms = step.ms if step.ms is not None else 1000
            self._page.wait_for_timeout(ms)
            return
        if action == "screenshot":
            self._page.screenshot(type="png")
            return

        raise ValueError(f"Unsupported action: {action}")

    def is_login_page(self) -> bool:
        if not self._page:
            return False
        url = self._page.url.lower()
        return "accounts.google.com" in url or "login" in url or "signin" in url

    def _is_blocked_action(self, step: Step) -> bool:
        text = " ".join(
            [
                step.url or "",
                step.selector or "",
                step.text or "",
                step.key or "",
            ]
        ).lower()
        if any(keyword in text for keyword in BLOCKED_KEYWORDS):
            return True
        return False

    def _is_search_selector(self, selector: str) -> bool:
        lowered = selector.lower()
        return "search" in lowered or "query" in lowered or "submit" in lowered

    def _is_login_selector(self, selector: str) -> bool:
        lowered = selector.lower()
        return "login" in lowered or "sign in" in lowered or "signin" in lowered

    def _first_available(self, selectors: list[str]) -> str | None:
        for selector in selectors:
            try:
                if self._page.locator(selector).first.is_visible(timeout=1500):
                    return selector
            except Exception:
                continue
        return None

    def _fill_first_available(self, selectors: list[str], text: str) -> None:
        selector = self._first_available(selectors)
        if not selector:
            raise PlaywrightTimeoutError("No search input found")
        self._page.fill(selector, text)

    def _click_first_available(self, selectors: list[str]) -> None:
        selector = self._first_available(selectors)
        if not selector:
            raise PlaywrightTimeoutError("No search button found")
        self._page.click(selector)


def _normalize_selector(selector: str) -> str:
    trimmed = selector.strip()
    lowered = trimmed.lower()
    if trimmed.lower().startswith("aria-label="):
        value = trimmed.split("=", 1)[1].strip().strip("\"").strip("'")
        return f'[aria-label="{value}"]'
    if lowered.startswith("name="):
        value = trimmed.split("=", 1)[1].strip().strip("\"").strip("'")
        return f'[name="{value}"]'
    if lowered.startswith("id="):
        value = trimmed.split("=", 1)[1].strip().strip("\"").strip("'")
        return f'#{value}'
    if trimmed.lower().startswith("text="):
        return trimmed
    return trimmed


def _sanitize_url(url: str) -> str:
    raw = url.strip()
    if " " not in raw and (raw.startswith("http://") or raw.startswith("https://")):
        return raw
    domain = _extract_domain(raw)
    if domain:
        return f"https://{domain}"
    # Fallback to Google search
    query = raw.replace(" ", "+")
    return f"https://www.google.com/search?q={query}"


def _extract_domain(text: str) -> str | None:
    lowered = text.lower().strip()
    url_match = re.search(r"https?://([^\s/]+)", lowered)
    if url_match:
        host = url_match.group(1).strip().strip(".").replace("www.", "")
        if host and "." in host and " " not in host:
            return host
    tokens = re.split(r"[\s,()]+", lowered)
    for token in tokens:
        cleaned = token.strip().strip(".")
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            cleaned = re.sub(r"^https?://", "", cleaned)
        cleaned = cleaned.replace("www.", "")
        if "." in cleaned and " " not in cleaned:
            return cleaned
    return None
