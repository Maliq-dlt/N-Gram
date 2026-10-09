"""Cooperative cancellation for native work; no forced thread termination."""

import shutil
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from threading import Event
from uuid import uuid4


class WorkCancelled(RuntimeError):
    pass


def check_cancel(cancel: Event | None = None) -> None:
    if cancel is not None and cancel.is_set():
        raise WorkCancelled("Proses dibatalkan; file dan hasil sebelumnya tetap tersimpan.")


def run_command(args, *, timeout=180, cancel=None, text=False):
    check_cancel(cancel)
    with subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text
    ) as process:
        deadline = time.monotonic() + timeout
        try:
            while True:
                check_cancel(cancel)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(args, timeout)
                try:
                    stdout, stderr = process.communicate(timeout=min(0.2, remaining))
                    return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
                except subprocess.TimeoutExpired:
                    continue
        except BaseException:
            process.kill()
            process.communicate()
            raise


@contextmanager
def working_directory(dir, prefix="work-"):
    """Inherit workspace access; tempfile's private ACL is unusable in the Windows sandbox."""
    from runtime import ROOT

    parent = Path(dir).resolve()
    if not parent.is_relative_to(ROOT.resolve()):
        raise ValueError("Temporary output must stay in the workspace.")
    target = parent / (prefix + uuid4().hex)
    target.mkdir()
    try:
        yield str(target)
    finally:
        # Only our newly-created directory; never a user-selected or computed ancestor.
        shutil.rmtree(target)
