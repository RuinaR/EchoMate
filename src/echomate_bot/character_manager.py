"""Opt-in single-resident character lifecycle, independent of Discord and DBs.

Backend API v1 owns its model/process and must prove reclamation, not infer it
from aggregate GPU free memory. No concrete backend is approved by this module.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Callable, Awaitable

from .character_models import CharacterModel, valid_name, with_identity


class State(str, Enum):
    IDLE = 'Idle'
    SWITCHING_REQUESTED = 'SwitchingRequested'
    QUIESCING = 'Quiescing'
    CANCELLING = 'Cancelling'
    UNLOADING = 'Unloading'
    RECLAIMING = 'Reclaiming'
    LOADING = 'Loading'
    VALIDATING = 'Validating'
    READY = 'Ready'
    FAILED = 'Failed'
    RECOVERY_REQUIRED = 'RecoveryRequired'


@dataclass(frozen=True)
class Identity:
    character_id: str
    epoch: int
    name_version: int
    name: str


class CharacterBackend(Protocol):
    async def validate(self, entry: CharacterModel) -> bool: ...
    async def load(self, entry: CharacterModel) -> None: ...
    async def generate(self, messages: list[dict]) -> str: ...
    async def cancel(self) -> None: ...
    async def unload(self) -> None: ...
    async def reclaimed(self) -> bool: ...
    async def health_check(self, entry: CharacterModel, name: str) -> bool: ...


class CharacterModelManager:
    """Stage-one lifecycle API. Caller must authorize owner actions separately.

    Resource admission is mandatory and may not load a model. Production wiring
    additionally requires character-scoped memories and send-time valid(stamp).
    A failed/timed-out cleanup keeps the backend owned and prevents new loading.
    """
    _resident_owner = None

    def __init__(self, factory: Callable[[CharacterModel], CharacterBackend],
                 admission: Callable[[CharacterModel], Awaitable[bool]], *, timeout=30):
        if timeout <= 0:
            raise ValueError('Positive lifecycle timeout required')
        self.factory = factory
        self.admission = admission
        self.timeout = timeout
        self.state = State.IDLE
        self.epoch = 0
        self.name_version = 0
        self.active: Identity | None = None
        self.entry: CharacterModel | None = None
        self.backend: CharacterBackend | None = None
        self.last_error: str | None = None
        self._lock = asyncio.Lock()
        self._gpu = asyncio.Lock()
        self._jobs = set()
        self._operations = set()

    def valid(self, stamp: Identity | None) -> bool:
        return stamp is not None and self.state == State.READY and stamp == self.active

    def _invalidate(self):
        self.epoch += 1
        self.active = None

    async def _bounded(self, awaitable):
        # wait_for can wait forever if a backend suppresses CancelledError.
        # Retain such operations explicitly, fail closed and forbid another load.
        task = asyncio.create_task(awaitable)
        self._operations.add(task)
        def finished(done):
            self._operations.discard(done)
            if not done.cancelled():
                done.exception()  # Retrieve late errors without exposing contents.
        task.add_done_callback(finished)
        try:
            done, _ = await asyncio.wait({task}, timeout=self.timeout)
            if not done:
                task.cancel()
                raise TimeoutError('Character lifecycle operation timed out')
            return task.result()
        except BaseException:
            if not task.done():
                task.cancel()
            raise

    async def _release(self):
        if self._operations:
            raise RuntimeError('Backend operation still running')
        self.state = State.CANCELLING
        for job in self._jobs:
            job.cancel()
        if self.backend:
            await self._bounded(self.backend.cancel())
        if self._jobs:
            _, pending = await asyncio.wait(self._jobs, timeout=self.timeout)
            if pending:
                raise TimeoutError('Generation did not drain')
        self.state = State.UNLOADING
        if self.backend:
            await self._bounded(self.backend.unload())
            self.state = State.RECLAIMING
            if await self._bounded(self.backend.reclaimed()) is not True:
                raise RuntimeError('Backend reclamation not verified')
            self.backend = None
        self.entry = None
        if CharacterModelManager._resident_owner is self:
            CharacterModelManager._resident_owner = None

    async def switch(self, entry: CharacterModel, name: str):
        name = valid_name(name)
        if entry.blocker:
            raise ValueError(entry.blocker)
        async with self._lock:
            if self.state == State.RECOVERY_REQUIRED:
                raise RuntimeError('Explicit recovery required')
            self.state = State.SWITCHING_REQUESTED
            self._invalidate()
            try:
                self.state = State.QUIESCING
                await self._release()
                if await self._bounded(self.admission(entry)) is not True:
                    raise RuntimeError('Resource admission denied')
                if CharacterModelManager._resident_owner not in (None, self):
                    raise RuntimeError('Another character manager owns the model')
                CharacterModelManager._resident_owner = self
                self.backend = self.factory(entry)
                if await self._bounded(self.backend.validate(entry)) is not True:
                    raise RuntimeError('Installation validation failed')
                self.state = State.LOADING
                await self._bounded(self.backend.load(entry))
                self.state = State.VALIDATING
                if await self._bounded(self.backend.health_check(entry, name)) is not True:
                    raise RuntimeError('Character identity health check failed')
                self.entry = entry
                self.name_version += 1
                self.active = Identity(entry.character_id, self.epoch, self.name_version, name)
                self.last_error = None
                self.state = State.READY
                return self.active
            except BaseException as exc:
                self.last_error = type(exc).__name__
                self.state = State.RECOVERY_REQUIRED
                # Retain ownership until explicit recover() drains and reclaims.
                # No detached cleanup coroutine can race a new switch/recovery.
                if self.backend is None and not self._operations:
                    self.state = State.FAILED
                raise

    async def recover(self):
        async with self._lock:
            self._invalidate()
            try:
                await self._release()
            except BaseException:
                self.state = State.RECOVERY_REQUIRED
                raise
            self.state = State.IDLE

    async def rename(self, name: str):
        name = valid_name(name)
        async with self._lock:
            if self.state != State.READY or self.active is None:
                raise RuntimeError('No ready character')
            previous = self.active
            self.state = State.QUIESCING
            self._invalidate()
            try:
                for job in self._jobs:
                    job.cancel()
                await self._bounded(self.backend.cancel())
                if self._jobs:
                    _, pending = await asyncio.wait(self._jobs, timeout=self.timeout)
                    if pending:
                        raise TimeoutError('Generation did not drain')
                if await self._bounded(self.backend.health_check(self.entry, name)) is not True:
                    raise RuntimeError('New name not verified')
                self.name_version += 1
                self.active = Identity(previous.character_id, self.epoch, self.name_version, name)
                self.state = State.READY
                return self.active
            except BaseException as exc:
                self.last_error = type(exc).__name__
                self.state = State.RECOVERY_REQUIRED
                raise

    async def generate(self, stamp: Identity, messages: list[dict]) -> str:
        if not self.valid(stamp):
            raise RuntimeError('Stale character identity')
        # The existing Runtime fair queue must remain outside this single GPU
        # execution gate; unrelated CPU/DB work is never locked here.
        task = asyncio.create_task(self._generate(stamp, messages))
        self._jobs.add(task)
        try:
            return await task
        finally:
            self._jobs.discard(task)

    async def _generate(self, stamp, messages):
        async with self._gpu:
            if not self.valid(stamp):
                raise RuntimeError('Stale queued character identity')
            result = await self.backend.generate(with_identity(self.entry, stamp.name, messages))
            if not self.valid(stamp):
                raise RuntimeError('Stale character callback')
            return result
