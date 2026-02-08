from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from server.browser.playwright_controller import PlaywrightController
from server.agent.models import Step
from server.websocket_manager import WebSocketManager

@dataclass
class PriceItem:
    title: str
    price: Optional[float]
    url: str

@dataclass
class PlatformResult:
    platform: str
    items: List[PriceItem]

PRICE_RE = re.compile(r"(\d+[\d,.]*)")

PLATFORMS = {
    "amazon": {
        "name": "Amazon",
        "search_url": "https://www.amazon.in/s?k={query}",
    },
    "flipkart": {
        "name": "Flipkart",
        "search_url": "https://www.flipkart.com/search?q={query}",
    },
    "meesho": {
        "name": "Meesho",
        "search_url": "https://www.meesho.com/search?q={query}",
    },
}


def _parse_goal(goal: str) -> tuple[str, Optional[float]]:
    lower = goal.lower()
    max_price = None
    m = re.search(r"under\s+([\d,]+)", lower)
    if m:
        max_price = float(m.group(1).replace(",", ""))
    product = re.sub(r"under\s+[\d,]+", "", goal, flags=re.I)
    product = product.replace("on amazon", "").replace("on flipkart", "").replace("on meesho", "")
    product = product.replace("on", " ").replace("price", " ")
    product = product.replace("  ", " ").strip()
    return product, max_price


def _money_to_float(text: str) -> Optional[float]:
    if not text:
        return None
    m = PRICE_RE.search(text.replace("?", ""))
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


async def run_price_compare(goal: str, manager: WebSocketManager, platforms: List[str]) -> None:
    product, max_price = _parse_goal(goal)
    await manager.send_log("info", f"Price compare: '{product}' under {max_price or 'no limit'}")

    async def _scrape(platform_key: str) -> PlatformResult:
        config = PLATFORMS[platform_key]
        controller = PlaywrightController(persistent=False)
        await controller.start()
        try:
            url = config["search_url"].format(query=_urlencode(product))
            await controller.perform_action(Step(action="navigate", url=url))
            await controller.perform_action(Step(action="wait", ms=1500))
            items = await asyncio.to_thread(_extract_items_sync, controller, platform_key)
            # Filter by max price
            if max_price is not None:
                items = [i for i in items if i.price is None or i.price <= max_price]
            # Keep top 3
            items = items[:3]
            # Send a frame snapshot for visibility
            frame = await controller.screenshot_base64()
            if frame:
                await manager.send_frame(frame, source=config["name"])
            return PlatformResult(platform=config["name"], items=items)
        finally:
            await controller.stop()

    tasks = [_scrape(p) for p in platforms]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    payload = {
        "query": product,
        "max_price": max_price,
        "results": [
            {
                "platform": r.platform,
                "items": [
                    {"title": i.title, "price": i.price, "url": i.url} for i in r.items
                ],
            }
            for r in results
        ],
    }
    await manager.send_event("PRICE_RESULTS", payload)


def _extract_items_sync(controller: PlaywrightController, platform_key: str) -> List[PriceItem]:
    page = controller._page  # type: ignore
    if page is None:
        return []

    if platform_key == "amazon":
        cards = page.locator("div[data-component-type='s-search-result']")
        count = min(cards.count(), 10)
        items: List[PriceItem] = []
        for i in range(count):
            card = cards.nth(i)
            title = card.locator("h2 a span").first.inner_text() if card.locator("h2 a span").count() else ""
            href = card.locator("h2 a").first.get_attribute("href") or ""
            price_whole = card.locator("span.a-price-whole").first.inner_text() if card.locator("span.a-price-whole").count() else ""
            price_frac = card.locator("span.a-price-fraction").first.inner_text() if card.locator("span.a-price-fraction").count() else ""
            price = _money_to_float(f"{price_whole}{price_frac}")
            url = f"https://www.amazon.in{href}" if href.startswith("/") else href
            if title:
                items.append(PriceItem(title=title, price=price, url=url))
        return items

    if platform_key == "flipkart":
        cards = page.locator("div[data-id]")
        count = min(cards.count(), 10)
        items = []
        for i in range(count):
            card = cards.nth(i)
            title = ""
            if card.locator("a[title]").count():
                title = card.locator("a[title]").first.get_attribute("title") or ""
                href = card.locator("a[title]").first.get_attribute("href") or ""
            else:
                title = card.locator("div._4rR01T").first.inner_text() if card.locator("div._4rR01T").count() else ""
                href = card.locator("a").first.get_attribute("href") if card.locator("a").count() else ""
            price_text = card.locator("div._30jeq3").first.inner_text() if card.locator("div._30jeq3").count() else ""
            price = _money_to_float(price_text)
            url = f"https://www.flipkart.com{href}" if href and href.startswith("/") else (href or "")
            if title:
                items.append(PriceItem(title=title, price=price, url=url))
        return items

    if platform_key == "meesho":
        cards = page.locator("a[href*='/product/']")
        count = min(cards.count(), 10)
        items = []
        for i in range(count):
            card = cards.nth(i)
            title = card.locator("p").first.inner_text() if card.locator("p").count() else ""
            href = card.get_attribute("href") or ""
            price_text = ""
            if card.locator("span").count():
                price_text = " ".join(card.locator("span").all_inner_texts())
            price = _money_to_float(price_text)
            url = f"https://www.meesho.com{href}" if href.startswith("/") else href
            if title:
                items.append(PriceItem(title=title, price=price, url=url))
        return items

    return []


def _urlencode(text: str) -> str:
    return (
        text.replace(" ", "+")
        .replace("\"", "")
        .replace("'", "")
        .replace("#", "")
        .replace("&", "and")
    )
