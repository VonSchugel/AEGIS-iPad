"""Bounded, cancellable subprocesses. This module never logs raw output."""
import asyncio
from dataclasses import dataclass
import sys
import os
import signal
from typing import Sequence


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    cancelled: bool = False
    output_truncated: bool = False


class ProcessRunner:
    def __init__(self, max_output: int = 1_048_576):
        self.max_output = max_output

    async def run(self, argv: Sequence[str], timeout: float = 15.0, *, interactive: bool = False, env: dict[str, str] | None = None) -> CommandResult:
        if not argv or timeout <= 0:
            raise ValueError("Nonempty argv and positive timeout required")
        args = tuple(str(a) for a in argv)
        output_truncated = False
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            stdin=None if interactive else asyncio.subprocess.DEVNULL,
            env=env,
            start_new_session=os.name == "posix",
        )

        async def collect(stream: asyncio.StreamReader) -> bytes:
            nonlocal output_truncated
            chunks, retained = [], 0
            while chunk := await stream.read(65536):
                if retained + len(chunk) > self.max_output:
                    output_truncated = True
                if interactive:
                    from aegis.evidence import redact
                    # Console guidance comes from the pinned upstream tool, never interpreted as instructions.
                    print(redact(chunk.decode("utf-8", errors="replace")), end="", file=sys.stderr, flush=True)
                if retained < self.max_output:
                    piece = chunk[: self.max_output - retained]
                    chunks.append(piece)
                    retained += len(piece)
            return b"".join(chunks)

        out_task = asyncio.create_task(collect(proc.stdout))
        err_task = asyncio.create_task(collect(proc.stderr))
        timed_out = False
        async def stop_tree():
            if os.name == "posix":
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif proc.returncode is None:
                proc.kill()
            try:
                await asyncio.wait_for(proc.wait(), 2.0)
            except asyncio.TimeoutError:
                # A detached descendant may retain a pipe after the direct process dies.
                # Group cleanup cannot terminate processes that deliberately left the group.
                pass
        try:
            await asyncio.wait_for(proc.wait(), timeout)
        except asyncio.TimeoutError:
            timed_out = True
            await stop_tree()
        except asyncio.CancelledError:
            await stop_tree()
            raise
        finally:
            # Descendants retaining inherited pipes cannot block cancellation forever.
            try:
                await asyncio.wait_for(asyncio.gather(out_task, err_task), 2.0)
            except asyncio.TimeoutError:
                out_task.cancel()
                err_task.cancel()
            # asyncio exposes no public Process.close(). Close the owned pipe
            # transports explicitly when an escaped descendant retained a handle.
            for stream in (proc.stdout, proc.stderr):
                transport = getattr(stream, "_transport", None)
                if transport is not None:
                    transport.close()
            await asyncio.sleep(0)
        def decoded(task):
            return "" if task.cancelled() else task.result().decode("utf-8", errors="replace")
        return CommandResult(args, proc.returncode, decoded(out_task), decoded(err_task), timed_out, False, output_truncated)
