"""Lifecycle manager for the sidecar background process."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Generator


class SidecarProcess:
    """Context manager that starts the sidecar, waits for it, then cleans up."""

    def __init__(
        self,
        sidecar_dir: str,
        socket_path: str = "/tmp/pokemon_sidecar.sock",
        startup_timeout: float = 10.0,
    ) -> None:
        self.sidecar_dir = sidecar_dir
        self.socket_path = socket_path
        self.startup_timeout = startup_timeout
        self._proc: subprocess.Popen | None = None

    def __enter__(self) -> str:
        sock = Path(self.socket_path)

        # Clean up stale socket from previous run
        if sock.exists():
            sock.unlink()

        env = dict(os.environ)
        env["POKEMON_SIDECAR_STUB"] = "1"
        env["POKEMON_SIDECAR_SOCK"] = self.socket_path
        # Unset any real API key so stub mode is forced
        env.pop("ANTHROPIC_API_KEY", None)

        self._proc = subprocess.Popen(
            ["uv", "run", "python", "-m", "pokemon_sidecar"],
            env=env,
            cwd=self.sidecar_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for socket file to appear
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if sock.exists():
                break
            if self._proc.poll() is not None:
                stdout = self._proc.stdout.read().decode(errors="replace") if self._proc.stdout else ""
                stderr = self._proc.stderr.read().decode(errors="replace") if self._proc.stderr else ""
                raise RuntimeError(
                    f"Sidecar exited prematurely (code {self._proc.returncode}).\n"
                    f"stdout: {stdout}\nstderr: {stderr}"
                )
            time.sleep(0.1)
        else:
            self._proc.kill()
            raise RuntimeError(
                f"Sidecar socket not created within {self.startup_timeout}s: {self.socket_path}"
            )

        return self.socket_path

    def __exit__(self, *_) -> None:
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.send_signal(signal.SIGTERM)
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        sock = Path(self.socket_path)
        if sock.exists():
            sock.unlink()
