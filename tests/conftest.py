"""Own the test session's asyncio policy without creating an unused loop."""

import asyncio
from collections.abc import Iterator

import pytest


@pytest.fixture(scope="session", autouse=True)
def event_loop_policy() -> Iterator[asyncio.AbstractEventLoopPolicy]:
    """Prevent pytest-asyncio 1.0 from lazily allocating an unowned old loop.

    Its scoped-loop fixture saves the policy's current loop before installing
    the test loop. An untouched Python 3.12 default policy creates a loop during
    that lookup, although no fixture owns or closes it. On Windows this leaks
    the Proactor self-pipe sockets. Start this isolated policy with an explicit
    None instead. pytest-asyncio and asyncio.run still own and close every loop
    they create; ResourceWarning remains an error when requested by the runner.
    """
    previous_policy = asyncio.get_event_loop_policy()
    policy = asyncio.DefaultEventLoopPolicy()
    policy.set_event_loop(None)
    asyncio.set_event_loop_policy(policy)
    try:
        yield policy
    finally:
        asyncio.set_event_loop_policy(previous_policy)
