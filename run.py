#!/usr/bin/env python3
"""Start the requirements & roles server. Stdlib only: no install step."""
import argparse

from app.server import serve

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Requirements & roles server")
    parser.add_argument("--port", type=int, default=8133)
    parser.add_argument("--db", default="data/school.db")
    args = parser.parse_args()
    serve(args.db, args.port)
