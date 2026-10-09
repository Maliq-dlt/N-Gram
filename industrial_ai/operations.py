"""Cooperative cancellation for native work; no forced thread termination."""

import subprocess
import time
from threading import Event


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
