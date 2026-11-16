#!/usr/bin/env python3
"""Start the Design Hub server. Stdlib only: no install step."""
import argparse

from app.server import serve

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Design Hub server")
    parser.add_argument("--port", type=int, default=8130)
    parser.add_argument("--db", default="data/hub.db")
    args = parser.parse_args()
    serve(args.db, args.port)
