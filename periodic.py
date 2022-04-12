import asyncio
from asyncio import Task
from contextlib import suppress
import traceback
from typing import Any, cast, Optional


class Periodic:

    def __init__(self, func, time: int):
        self._func = func
        self._time = time
        self._is_started = False
        self.__task: Optional[Task[Any]] = None

    async def start(self) -> None:
        if not self._is_started:
            self._is_started = True
            # Start task to call func periodically:
            self.__task = cast(Task[Any], asyncio.ensure_future(self._run()))

    async def stop(self) -> None:
        if self._is_started:
            self._is_started = False
            # Stop task and await it stopped:
            if self.__task is not None:
                self.__task.cancel()
                with suppress(asyncio.CancelledError):
                    await self.__task

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._time)
            try:
                self._func()
            except Exception as e:
                traceback.print_tb(e.__traceback__)
