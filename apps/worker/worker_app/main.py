from __future__ import annotations

import argparse
from worker_app.jobs.document_indexing import run_forever, run_once


def main() -> None:
    parser = argparse.ArgumentParser(description="Archyve local indexing worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one pending indexing job and exit.",
    )
    args = parser.parse_args()

    if args.once:
        run_once()
        return

    run_forever()


if __name__ == "__main__":
    main()
