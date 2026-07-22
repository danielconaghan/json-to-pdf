"""Run the web UI: ``python -m webui`` (or ``make ui``).

    python -m webui                 # http://127.0.0.1:8000  (localhost only)
    python -m webui --host 0.0.0.0  # reachable from other machines on the LAN
    python -m webui --port 9000
"""
import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m webui", description=__doc__)
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="interface to bind (default 127.0.0.1; use 0.0.0.0 for LAN access)",
    )
    parser.add_argument("--port", type=int, default=8000, help="port (default 8000)")
    parser.add_argument(
        "--reload", action="store_true", help="auto-reload on code changes (dev)"
    )
    args = parser.parse_args()

    uvicorn.run(
        "webui.server:app", host=args.host, port=args.port, reload=args.reload
    )


if __name__ == "__main__":
    main()
