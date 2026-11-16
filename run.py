#!/usr/bin/env python3
"""Start the School Management System API + dashboard."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from school.app import create_server
from school.auth import AuthService
from school.service import SchoolService
from school.seed import seed
from school.store import Store


def main():
    parser = argparse.ArgumentParser(description="School Management System")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--seed", action="store_true",
                        help="load demo data on first run")
    parser.add_argument("--data", default=None, help="path to JSON data file")
    args = parser.parse_args()

    data_path = args.data or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "school.json")
    store = Store(data_path)
    auth = AuthService(store)
    service = SchoolService(store, auth)
    if args.seed and seed(auth, service):
        print("Seeded demo data (admin/admin123, teacher/teacher123, ...).")

    server = create_server(args.port, data_path)
    print(f"SchoolMS running at http://127.0.0.1:{args.port}/ (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
