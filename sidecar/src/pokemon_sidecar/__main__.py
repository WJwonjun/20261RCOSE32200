from __future__ import annotations

import uvloop

from .server import run_server

if __name__ == "__main__":
    uvloop.run(run_server())
