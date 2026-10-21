"""Real host-only subprocess tests; no Apple utility or USB device is used."""

import asyncio
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from aegis.adapters.process import ProcessRunner


@pytest.mark.asyncio
async def test_exit_status_and_separate_streams_are_preserved():
    argv = [sys.executable, "-c", "import sys; print('ordinary output'); print('diagnostic output', file=sys.stderr); sys.exit(7)"]
    result = await ProcessRunner().run(argv, timeout=10)
    assert result.argv == tuple(argv)
    assert result.returncode == 7
    assert result.stdout.strip() == "ordinary output"
    assert result.stderr.strip() == "diagnostic output"
    assert not result.timed_out


@pytest.mark.asyncio
async def test_large_output_is_drained_without_exceeding_retained_caps():
    code = "import sys; sys.stdout.write('a'*300000); sys.stdout.flush(); sys.stderr.write('b'*300000); sys.stderr.flush()"
    result = await ProcessRunner(max_output=137).run([sys.executable, "-c", code], timeout=10)
    assert result.returncode == 0
    assert result.stdout == "a" * 137
    assert result.stderr == "b" * 137
    assert not result.timed_out


@pytest.mark.asyncio
async def test_arguments_are_literal_and_cannot_invoke_a_shell(tmp_path):
    marker = tmp_path / "must-not-exist.txt"
    argument = f"; echo INJECTED > '{marker}' & $(echo ignored) `echo ignored` | cat"
    result = await ProcessRunner().run([sys.executable, "-c", "import sys; print(sys.argv[1])", argument], timeout=10)
    assert result.returncode == 0
    assert result.stdout.strip() == argument
    assert not marker.exists()


@pytest.mark.asyncio
async def test_explicit_environment_does_not_inherit_unlisted_variables(monkeypatch):
    monkeypatch.setenv("AEGIS_PROCESS_PARENT_MARKER", "must-not-reach-child")
    child_env = {"AEGIS_PROCESS_CHILD_MARKER": "expected"}
    if "SYSTEMROOT" in os.environ:
        child_env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    code = "import json, os; print(json.dumps([os.getenv('AEGIS_PROCESS_CHILD_MARKER'),os.getenv('AEGIS_PROCESS_PARENT_MARKER')]))"
    result = await ProcessRunner().run([sys.executable, "-c", code], timeout=10, env=child_env)
    assert result.returncode == 0
    assert json.loads(result.stdout) == ["expected", None]


@pytest.mark.asyncio
async def test_timeout_stops_a_blocked_local_process_within_bound():
    started = time.monotonic()
    result = await ProcessRunner().run([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.25)
    assert result.timed_out
    assert result.returncode is not None and result.returncode != 0
    assert time.monotonic() - started < 6


async def _wait_for_file(path: Path, task: asyncio.Task, seconds: float = 8) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.is_file():
            return
        if task.done():
            await task
            raise AssertionError("Child exited before writing its readiness observation")
        await asyncio.sleep(0.02)
    raise AssertionError("Host subprocess did not become ready within the test bound")


@pytest.mark.asyncio
async def test_cancellation_propagates_and_cleanup_is_bounded(tmp_path):
    marker = tmp_path / "ready.txt"
    code = "from pathlib import Path; import sys,time; Path(sys.argv[1]).write_text('ready'); time.sleep(30)"
    task = asyncio.create_task(ProcessRunner().run([sys.executable, "-c", code, str(marker)], timeout=20))
    try:
        await _wait_for_file(marker, task)
        started = time.monotonic()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 6)
        assert time.monotonic() - started < 6
    finally:
        if not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, 6)
            except (asyncio.CancelledError, TimeoutError):
                pass


@pytest.mark.asyncio
async def test_timeout_cleanup_is_bounded_when_a_detached_child_retains_pipes(tmp_path):
    """Unexpected descendants must not make the caller's timeout unbounded.

    The test owns and explicitly cleans up the detached sleeper. It does not
    assert that killing an isolated process group can kill an escaped session.
    """
    observed = tmp_path / "detached.json"
    code = (
        "import json,subprocess,sys,time; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'],start_new_session=True); "
        "open(sys.argv[1],'w').write(json.dumps({'child':child.pid})); time.sleep(20)"
    )
    started = time.monotonic()
    task = asyncio.create_task(ProcessRunner().run([sys.executable, "-c", code, str(observed)], timeout=0.8))
    child_pid = None
    cleanup_task = None

    async def guaranteed_test_cleanup():
        await asyncio.sleep(6)
        try:
            os.kill(child_pid, signal.SIGTERM)
        except OSError:
            pass

    try:
        await _wait_for_file(observed, task)
        child_pid = json.loads(observed.read_text())["child"]
        assert child_pid != os.getpid()
        cleanup_task = asyncio.create_task(guaranteed_test_cleanup())
        result = await task
        assert result.timed_out
        assert time.monotonic() - started < 5.5, "The process wait blocked on a detached child's inherited pipes"
    finally:
        if child_pid is not None and child_pid != os.getpid():
            try:
                os.kill(child_pid, signal.SIGTERM)
            except OSError:
                pass
        if cleanup_task is not None:
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
        if not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, 6)
            except (asyncio.CancelledError, TimeoutError):
                pass


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # A killed orphan can remain a zombie until reaped by PID 1. It cannot run
    # device operations, and must not be mistaken for a surviving worker.
    proc_stat = Path(f"/proc/{pid}/stat")
    if proc_stat.is_file():
        try:
            return proc_stat.read_text().rsplit(") ", 1)[1].split()[0] != "Z"
        except (OSError, IndexError):
            return False
    status = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, timeout=3)
    return bool(status.stdout.strip()) and not status.stdout.lstrip().startswith("Z")


@pytest.mark.skipif(os.name != "posix", reason="Physical palera1n hosts use POSIX process groups; this Windows host cannot verify them")
@pytest.mark.parametrize("stop_kind", ["timeout", "cancel"])
@pytest.mark.asyncio
async def test_posix_cancellation_and_timeout_stop_child_and_grandchild(tmp_path, stop_kind):
    observed = tmp_path / "tree.json"
    child_code = (
        "import json,os,subprocess,sys,time; "
        "grandchild=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
        "open(sys.argv[1],'w').write(json.dumps({'parent':os.getppid(),'child':os.getpid(),'grandchild':grandchild.pid})); "
        "time.sleep(30)"
    )
    parent_code = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]]); time.sleep(30)"
    timeout = 2 if stop_kind == "timeout" else 20
    task = asyncio.create_task(ProcessRunner().run([sys.executable, "-c", parent_code, child_code, str(observed)], timeout=timeout))
    pids = {}
    try:
        await _wait_for_file(observed, task)
        pids = json.loads(observed.read_text())
        assert all(pid != os.getpid() for pid in pids.values())
        if stop_kind == "cancel":
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, 6)
        else:
            result = await asyncio.wait_for(task, 8)
            assert result.timed_out
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and any(_pid_is_running(pid) for pid in pids.values()):
            await asyncio.sleep(0.02)
        assert not any(_pid_is_running(pid) for pid in pids.values())
    finally:
        if not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, 6)
            except (asyncio.CancelledError, TimeoutError):
                pass
        for pid in pids.values():
            if pid != os.getpid():
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
