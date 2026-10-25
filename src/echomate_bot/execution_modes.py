"""Execution capability boundaries; a local success is no social certificate."""
from enum import Enum


class ExecutionMode(str, Enum):
    LOCAL_CHAT='LOCAL_CHAT'
    DISCORD_DIRECT='DISCORD_DIRECT'
    DISCORD_AUTONOMOUS='DISCORD_AUTONOMOUS'


def local_ready(technical, identity):
    return bool(technical and identity)
