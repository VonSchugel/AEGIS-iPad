import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from aegis.models import WorkflowError
from aegis.safety.session import hardware_session


PROBE = """
from pathlib import Path
import sys
from aegis.models import WorkflowError
from aegis.safety.session import hardware_session
try:
    with hardware_session(Path(sys.argv[1])):
        print('OWNED', flush=True)
        if len(sys.argv) > 2:
            import time
            Path(sys.argv[1]).with_suffix('.ready').write_text('OWNED')
            time.sleep(30)
except WorkflowError as error:
    print(error.code, flush=True)
    sys.exit(17)
"""


def probe(path):
    return subprocess.run([sys.executable, "-c", PROBE, str(path)], capture_output=True, text=True, timeout=10)


def test_cross_process_exclusion_and_release_without_deleting_file(tmp_path):
    path = tmp_path / "session.lock"
    with hardware_session(path):
        blocked = probe(path)
        assert blocked.returncode == 17 and blocked.stdout.strip() == "HARDWARE_SESSION_BUSY"
        with pytest.raises(WorkflowError, match="Another AEGIS"):
            with hardware_session(path):
                pytest.fail("Second owner entered")
    assert path.exists()
    released = probe(path)
    assert released.returncode == 0 and released.stdout.strip() == "OWNED"


def test_kernel_releases_lock_after_owner_process_is_killed(tmp_path):
    path = tmp_path / "session.lock"
    with subprocess.Popen([sys.executable, "-c", PROBE, str(path), "hold"], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as owner:
        try:
            # Wait for a bounded acquisition signal, not an assumed startup delay.
            deadline = time.monotonic() + 5
            while not path.with_suffix('.ready').exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert path.with_suffix('.ready').read_text() == 'OWNED'
            assert probe(path).returncode == 17
        finally:
            owner.kill()
            owner.communicate(timeout=5)
    assert probe(path).returncode == 0


def test_releases_on_body_error_and_does_not_mask_it(tmp_path):
    path = tmp_path / "session.lock"
    with pytest.raises(RuntimeError, match="test failure"):
        with hardware_session(path):
            raise RuntimeError("test failure")
    assert probe(path).returncode == 0


def test_invalid_lock_target_blocks_without_hardware(tmp_path):
    with pytest.raises(WorkflowError, match="Cannot establish"):
        with hardware_session(tmp_path):
            pytest.fail("Directory accepted as lock")


@pytest.mark.skipif(os.name == "nt", reason="Unprivileged Windows symlink creation is not assured")
def test_symbolic_link_lock_is_rejected(tmp_path):
    real = tmp_path / "real"
    real.touch()
    linked = tmp_path / "link"
    linked.symlink_to(real)
    with pytest.raises(WorkflowError, match="Cannot establish"):
        with hardware_session(linked):
            pytest.fail("Symlink accepted")
