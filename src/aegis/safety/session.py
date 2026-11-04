"""Fail-fast OS lock for cooperating AEGIS hardware commands, per OS user.

The lock file persists: unlinking it would permit two separately locked inodes.
The kernel releases ownership on process exit. No PID-based stale-lock stealing,
automatic retries, device identifiers, or device access are involved.
"""

from contextlib import contextmanager
import errno
import os
from pathlib import Path
import stat

from aegis.models import WorkflowError


@contextmanager
def hardware_session(path: Path | None = None):
    """Serialize cooperating commands across databases and repository copies.

    Uses a private, local user directory by default. This is an advisory lock;
    other programs, other users and direct low-level adapter callers can ignore
    it. A lock is coordination, never authorization or a safe-resume guarantee.
    """
    target = path if path is not None else Path.home() / ".aegis" / "hardware-session.lock"
    descriptor = None
    locked = False
    try:
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if target.is_symlink():
            raise OSError("Lock must not be a symbolic link")
        descriptor = os.open(target, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), 0o600)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError("Lock must be a regular file")
        os.set_inheritable(descriptor, False)
        try:
            if os.name == "nt":
                import msvcrt
                # Windows permits byte locks beyond EOF; no contender writes.
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError as error:
            if error.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                os.close(descriptor)
                descriptor = None
                raise WorkflowError("HARDWARE_SESSION_BUSY", "Another AEGIS hardware command is active; wait for it to finish before collecting fresh evidence") from None
            raise
    except OSError:
        if descriptor is not None:
            os.close(descriptor)
            descriptor = None
        raise WorkflowError("HARDWARE_LOCK_UNAVAILABLE", "Cannot establish the local hardware session lock; no hardware operation started") from None
    try:
        yield
    finally:
        if descriptor is not None:
            try:
                if locked:
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
