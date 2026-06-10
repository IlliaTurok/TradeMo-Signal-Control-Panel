"""Backward-compatible launcher for the old entry point.

Prefer running app.py directly.
"""

import asyncio

from app import main


if __name__ == "__main__":
    asyncio.run(main())