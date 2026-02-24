from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.db import apply_reference_menu, init_db


async def main() -> None:
    db_path = os.getenv("DB_PATH", "data/cafe.db")
    # Ensure schema exists
    await init_db(db_path)
    # Sync menu to reference
    await apply_reference_menu(db_path)
    print(f"OK: reference menu applied to {db_path}")


if __name__ == "__main__":
    asyncio.run(main())
