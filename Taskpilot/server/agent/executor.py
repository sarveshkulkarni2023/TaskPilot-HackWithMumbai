import re
import time
from typing import List
from server.agent.models import Step
from server.agent.safety import SafeModeBlocked
from server.websocket_manager import WebSocketManager
from server.browser.playwright_controller import PlaywrightController
from server.config import settings

class Executor:
    def __init__(self, manager: WebSocketManager, controller: PlaywrightController) -> None:
        self._manager = manager
        self._controller = controller

    async def execute_steps(self, steps: List[Step]) -> None:
        for index, step in enumerate(steps):
            await self._manager.send_event("STEP_STARTED", {"index": index, "step": step.model_dump()})
            await self._manager.send_log("info", f"Executing step {index + 1}: {step.action}")
            start = time.perf_counter()
            try:
                if step.action == "navigate" and step.url:
                    step.url = _sanitize_url(step.url, original_goal=step.url)
                if self._is_credential_step(step):
                    creds = await self._manager.request_credentials(
                        {
                            "username": "user" in (step.selector or "") or "email" in (step.selector or ""),
                            "email": "email" in (step.selector or ""),
                            "password": "password" in (step.selector or ""),
                        }
                    )
                    if step.selector:
                        if "password" in step.selector and creds.get("password"):
                            step.text = creds["password"]
                        elif "email" in step.selector and creds.get("email"):
                            step.text = creds["email"]
                        elif creds.get("username"):
                            step.text = creds["username"]
                await self._controller.perform_action(step)
                if self._controller.is_login_page():
                    await self._manager.send_log(
                        "info",
                        f"Login page detected. Waiting {settings.login_wait_ms}ms for manual login.",
                    )
                    await self._controller.perform_action(
                        Step(action="wait", ms=settings.login_wait_ms)
                    )
                duration_ms = int((time.perf_counter() - start) * 1000)
                await self._manager.send_event(
                    "STEP_COMPLETED",
                    {"index": index, "step": step.model_dump(), "duration_ms": duration_ms},
                )
                await self._manager.send_log("info", f"Completed step {index + 1}")
            except Exception as exc:
                duration_ms = int((time.perf_counter() - start) * 1000)
                await self._manager.send_event(
                    "STEP_FAILED",
                    {
                        "index": index,
                        "step": step.model_dump(),
                        "duration_ms": duration_ms,
                        "error": str(exc),
                    },
                )
                await self._manager.send_log("error", f"Step failed: {exc}")
                if isinstance(exc, SafeModeBlocked):
                    raise

    def _is_credential_step(self, step: Step) -> bool:
        if step.action != "type":
            return False
        selector = (step.selector or "").lower()
        if "password" in selector or "username" in selector or "email" in selector:
            if not step.text or step.text.strip() == "":
                return True
        return False


def _sanitize_url(url: str, original_goal: str | None = None) -> str:
    """
    Ensure navigation URL is valid.
    Never reconstruct URLs from full sentences.
    """

    if not url:
        return "https://www.google.com"

    cleaned = url.strip()

    # If already a valid URL, use it directly
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        if " " not in cleaned:
            return cleaned

    # Try extracting URL from text
    import re
    match = re.search(r"https?://[^\s]+", cleaned)
    if match:
        return match.group(0)

    # Fallback to Google search
    query = (original_goal or cleaned).replace(" ", "+")
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
