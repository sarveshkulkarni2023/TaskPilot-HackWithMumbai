import asyncio
from typing import List
from server.agent.planner import Planner
from server.agent.executor import Executor
from server.agent.models import Step
from server.websocket_manager import WebSocketManager
from server.browser.playwright_controller import PlaywrightController
from server.config import settings
from server.agent.price_compare import run_price_compare

async def _frame_loop(manager: WebSocketManager, controller: PlaywrightController, stop_event: asyncio.Event) -> None:
    """Stream live browser screenshots to the frontend in real time."""
    interval = settings.ws_frame_interval_ms / 1000.0
    while not stop_event.is_set():
        try:
            frame = await controller.screenshot_base64()
            if frame:
                source = await controller.get_current_url()
                await manager.send_frame(frame, source=source)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(interval)

async def run_agent(goal: str, manager: WebSocketManager) -> None:
    try:
        if _is_price_compare(goal):
            await manager.send_log("info", "Price comparison mode: parallel platforms")
            await manager.send_event("TASK_STARTED", {"goal": goal, "steps": []})
            await run_price_compare(goal, manager, ["amazon", "flipkart", "meesho"])
            await manager.send_event("TASK_COMPLETED", {"goal": goal})
            return

        planner = Planner()
        controller = PlaywrightController()
        executor = Executor(manager, controller)
        stop_event = asyncio.Event()

        await manager.send_log("info", "Planning steps")
        steps: List[Step] = await asyncio.to_thread(planner.generate_steps, goal)
        await manager.send_log("info", f"Plan source: {planner.last_plan_source}")

        await manager.send_log("info", "Starting browser")
        await controller.start()
        frame_task = asyncio.create_task(_frame_loop(manager, controller, stop_event))

        try:
            await manager.send_event("TASK_STARTED", {"goal": goal, "steps": [s.model_dump() for s in steps]})
            await executor.execute_steps(steps)
            await manager.send_event("TASK_COMPLETED", {"goal": goal})
        except Exception as exc:
            await manager.send_log("error", f"Execution error: {exc}")
            await manager.send_event("TASK_COMPLETED", {"goal": goal, "error": str(exc)})
        finally:
            stop_event.set()
            try:
                frame_task.cancel()
                await frame_task
            except asyncio.CancelledError:
                pass
            await controller.stop()

    except Exception as exc:
        await manager.send_log("error", f"Agent error: {exc}")
        await manager.send_event("TASK_COMPLETED", {"goal": goal, "error": str(exc)})


def _is_price_compare(goal: str) -> bool:
    lower = goal.lower()
    has_price_signal = "under" in lower or "below" in lower
    has_compare_signal = "price compare" in lower or "compare price" in lower or "compare" in lower
    has_platform_signal = "amazon" in lower or "flipkart" in lower or "meesho" in lower
    return (has_price_signal and has_platform_signal) or has_compare_signal
