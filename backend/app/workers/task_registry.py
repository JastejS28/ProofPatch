import asyncio
from collections.abc import Coroutine
from typing import Any


background_tasks: set[asyncio.Task[Any]] = set()


def _task_finished(task: asyncio.Task[Any]) -> None:
    background_tasks.discard(task)

    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        print(
            f"Background task failed: "
            f"{type(exc).__name__}: {exc}"
        )


def start_background_task(
    coroutine: Coroutine[Any, Any, Any],
) -> None:
    task = asyncio.create_task(coroutine)

    background_tasks.add(task)

    task.add_done_callback(_task_finished)