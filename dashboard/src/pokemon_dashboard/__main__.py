import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Pokemon Champions Dashboard")
    parser.add_argument("--host", default=os.environ.get("POKEMON_DASHBOARD_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("POKEMON_DASHBOARD_PORT", "8765")))
    args = parser.parse_args()

    uvicorn.run(
        "pokemon_dashboard.server:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
