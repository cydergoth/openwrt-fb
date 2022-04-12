import sys
import time
import logging
import asyncio
from contextlib import suppress


class Periodic:

    def __init__(self, func, time):
        self._func = func
        self._time = time
        self._is_started = False
        self.__task = None

    async def start(self):
       if not self._is_started:
           self._is_started = True
           # Start task to call func periodically:
           self.__task = asyncio.ensure_future(self._run())

    async def stop(self):
       if self._is_started:
           self._is_started = False
           # Stop task and await it stopped:
           self.__task.cancel()
           with suppress(asyncio.CancelledError):
                await self.__task

    async def _run(self):
        while True:
           await asyncio.sleep(self._time)
           try:
                self._func()
           except Exception as e:
                traceback.print_exc(e)
