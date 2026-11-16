"""Project launcher: `python run.py` serves the delivery app + dashboard."""
from __future__ import annotations

import sys

from delivery import seed
from delivery.config import DB_PATH, SERVER_HOST, SERVER_PORT
from delivery.server import serve
from delivery.store import connect, migrate


def main(argv: list[str]) -> int:
    db_path = DB_PATH
    if "--seed-only" in argv:
        conn = connect(db_path)
        migrate(conn)
        counts = seed.seed(conn)
        conn.close()
        print(f"seeded {db_path}: {counts}")
        return 0
    if "--port" in argv:
        try:
            port = int(argv[argv.index("--port") + 1])
        except (IndexError, ValueError):
            print("usage: python run.py [--port N] [--seed-only]", file=sys.stderr)
            return 2
    else:
        port = SERVER_PORT
    server = serve(host=SERVER_HOST, port=port, db_path=db_path)
    print(f"SchoolMS delivery app on http://{SERVER_HOST}:{port} (db={db_path})")
    print("Open that URL in a browser to use the dashboard.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
