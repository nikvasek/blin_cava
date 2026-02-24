from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import aiosqlite


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def reference_menu_items() -> list[tuple[str, str, str, int]]:
    # Prices are stored in kopeks (RUB * 100)
    return [
        (
            "Основные блюда",
            "Гриль стейк",
            "Стейк из говядины с картофелем айдахо и томатным соусом",
            93000,
        ),
        (
            "Основные блюда",
            "Палтус с бурым рисом",
            "Нежное филе палтуса с гарниром из пряного риса",
            89000,
        ),
        (
            "Основные блюда",
            "Антрекот",
            "Антрекот из говядины с зеленым горошком и пюре из цветной капусты",
            83000,
        ),
        (
            "Основные блюда",
            "Цыпленок по-итальянски",
            "Запеченный цыпленок с овощами и соусом песто",
            67000,
        ),
        (
            "Основные блюда",
            "Отбивная из свинины",
            "Жареная свинина на сковороде с сыром и картофельным пюре",
            74000,
        ),
        (
            "Напитки",
            "Домашний лимонад",
            "Лимонад на минеральной воде с добавлением розмарина",
            23000,
        ),
        ("Напитки", "Морс", "Морс из черной смородины", 16000),
        (
            "Напитки",
            "Свежевыжатый сок",
            "Сок на выбор: яблоко, апельсин, груша, киви",
            32000,
        ),
        (
            "Закуски",
            "Арбуз пекорино",
            "Кусочки арбуза с сыром пекорино, базиликом, мятой",
            25000,
        ),
        (
            "Закуски",
            "Брускетта с крабом",
            "Крабовое мясо на деревенском хлебе со огурцами и соусом",
            39000,
        ),
        (
            "Закуски",
            "Страчателла",
            "Сыр страчателла с томатами, клубникой и базиликом",
            45000,
        ),
    ]


@dataclass(frozen=True)
class MenuItem:
    id: int
    category: str
    title: str
    description: str
    price_cents: int
    is_active: int


@dataclass(frozen=True)
class CafeTable:
    id: int
    code: str
    seats: int
    zone: str
    is_active: int


@dataclass(frozen=True)
class CafeOrder:
    id: int
    user_id: int
    type: str
    status: str
    created_at: str
    scheduled_for: Optional[str]
    name: str
    phone: str
    address: Optional[str]
    comment: str
    total_cents: int


@dataclass(frozen=True)
class Reservation:
    id: int
    user_id: int
    table_id: int
    table_code: str
    start_at: str
    end_at: str
    guests: int
    name: str
    phone: str
    status: str
    created_at: str


def _dt_to_iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat(sep=" ")


def _iso_to_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


async def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        await db.executescript(schema_sql)
        await db.commit()

        await _seed_if_empty(db)
        await db.commit()


async def _seed_if_empty(db: aiosqlite.Connection) -> None:
    tables = [
        ("T1", 2, "main"),
        ("T2", 2, "main"),
        ("T3", 2, "main"),
        ("T4", 4, "main"),
        ("T5", 4, "main"),
        ("T6", 4, "main"),
        ("T7", 6, "main"),
        ("T8", 2, "main"),
        ("T9", 4, "main"),
        ("T10", 6, "main"),
    ]
    await db.executemany(
        "INSERT OR IGNORE INTO cafe_table(code, seats, zone) VALUES (?, ?, ?)",
        tables,
    )

    cur = await db.execute("SELECT COUNT(*) FROM menu_item")
    (menu_count,) = await cur.fetchone()
    await cur.close()
    if menu_count == 0:
        items = reference_menu_items()
        await db.executemany(
            "INSERT INTO menu_item(category, title, description, price_cents) VALUES (?, ?, ?, ?)",
            items,
        )


async def apply_reference_menu(db_path: str) -> None:
    """Make active menu match the reference menu.

    Safe for existing data: old items are deactivated (is_active=0) rather than deleted,
    so historical orders referencing old menu_item ids remain valid.
    """

    items = reference_menu_items()
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys=ON;")
        await db.execute("UPDATE menu_item SET is_active = 0")

        for category, title, description, price_cents in items:
            cur = await db.execute(
                "SELECT id FROM menu_item WHERE category = ? AND title = ? LIMIT 1",
                (category, title),
            )
            row = await cur.fetchone()
            await cur.close()

            if row:
                (item_id,) = row
                await db.execute(
                    """
                    UPDATE menu_item
                    SET description = ?, price_cents = ?, is_active = 1
                    WHERE id = ?
                    """,
                    (description, int(price_cents), int(item_id)),
                )
            else:
                await db.execute(
                    """
                    INSERT INTO menu_item(category, title, description, price_cents, is_active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (category, title, description, int(price_cents)),
                )

        await db.commit()


async def fetch_categories(db_path: str) -> list[str]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            "SELECT DISTINCT category FROM menu_item WHERE is_active = 1 ORDER BY category"
        )
        rows = await cur.fetchall()
        await cur.close()
    return [r[0] for r in rows]


async def fetch_menu_items(db_path: str, category: str) -> list[MenuItem]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT id, category, title, description, price_cents, is_active
            FROM menu_item
            WHERE is_active = 1 AND category = ?
            ORDER BY id
            """,
            (category,),
        )
        rows = await cur.fetchall()
        await cur.close()
    return [MenuItem(*row) for row in rows]


async def fetch_active_menu_items(db_path: str) -> list[MenuItem]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT id, category, title, description, price_cents, is_active
            FROM menu_item
            WHERE is_active = 1
            ORDER BY category, id
            """
        )
        rows = await cur.fetchall()
        await cur.close()
    return [MenuItem(*row) for row in rows]


async def fetch_menu_item(db_path: str, item_id: int) -> Optional[MenuItem]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT id, category, title, description, price_cents, is_active
            FROM menu_item
            WHERE id = ?
            """,
            (item_id,),
        )
        row = await cur.fetchone()
        await cur.close()
    return MenuItem(*row) if row else None


async def update_menu_item_price(db_path: str, item_id: int, price_cents: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE menu_item SET price_cents = ? WHERE id = ?",
            (int(price_cents), int(item_id)),
        )
        await db.commit()


async def fetch_menu_item_by_category_title(
    db_path: str,
    *,
    category: str,
    title: str,
) -> Optional[MenuItem]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT id, category, title, description, price_cents, is_active
            FROM menu_item
            WHERE is_active = 1 AND category = ? AND title = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (category, title),
        )
        row = await cur.fetchone()
        await cur.close()
    return MenuItem(*row) if row else None


async def fetch_tables(db_path: str, min_seats: int) -> list[CafeTable]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT id, code, seats, zone, is_active
            FROM cafe_table
            WHERE is_active = 1 AND seats >= ?
            ORDER BY seats, code
            """,
            (min_seats,),
        )
        rows = await cur.fetchall()
        await cur.close()
    return [CafeTable(*row) for row in rows]


async def fetch_table(db_path: str, table_id: int) -> Optional[CafeTable]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT id, code, seats, zone, is_active
            FROM cafe_table
            WHERE id = ?
            """,
            (table_id,),
        )
        row = await cur.fetchone()
        await cur.close()
    return CafeTable(*row) if row else None


async def table_is_available(
    db_path: str,
    table_id: int,
    start_at: datetime,
    end_at: datetime,
) -> bool:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT COUNT(*)
            FROM reservation
            WHERE
                table_id = ?
                AND status IN ('pending', 'confirmed')
                AND NOT (end_at <= ? OR start_at >= ?)
            """,
            (table_id, _dt_to_iso(start_at), _dt_to_iso(end_at)),
        )
        (cnt,) = await cur.fetchone()
        await cur.close()
    return cnt == 0


async def create_reservation(
    db_path: str,
    *,
    user_id: int,
    table_id: int,
    start_at: datetime,
    guests: int,
    name: str,
    phone: str,
) -> int:
    end_at = start_at + timedelta(hours=2, minutes=15)
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            INSERT INTO reservation(user_id, table_id, start_at, end_at, guests, name, phone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                user_id,
                table_id,
                _dt_to_iso(start_at),
                _dt_to_iso(end_at),
                guests,
                name,
                phone,
            ),
        )
        await db.commit()
        reservation_id = cur.lastrowid
        await cur.close()
    return int(reservation_id)


async def create_order(
    db_path: str,
    *,
    user_id: int,
    order_type: str,
    scheduled_for: Optional[datetime],
    name: str,
    phone: str,
    address: Optional[str],
    comment: str,
    items: list[dict[str, Any]],
) -> int:
    total_cents = sum(int(it["price_cents"]) * int(it["qty"]) for it in items)
    scheduled_for_iso = _dt_to_iso(scheduled_for) if scheduled_for else None
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            INSERT INTO cafe_order(user_id, type, status, scheduled_for, name, phone, address, comment, total_cents)
            VALUES (?, ?, 'new', ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                order_type,
                scheduled_for_iso,
                name,
                phone,
                address,
                comment,
                total_cents,
            ),
        )
        order_id = int(cur.lastrowid)
        await cur.close()

        await db.executemany(
            """
            INSERT INTO cafe_order_item(order_id, menu_item_id, qty, item_price_cents, comment)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    order_id,
                    int(it["menu_item_id"]),
                    int(it["qty"]),
                    int(it["price_cents"]),
                    str(it.get("comment", "")),
                )
                for it in items
            ],
        )

        await db.commit()
    return order_id


async def fetch_recent_orders(db_path: str, *, limit: int = 20) -> list[CafeOrder]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT id, user_id, type, status, created_at, scheduled_for, name, phone, address, comment, total_cents
            FROM cafe_order
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = await cur.fetchall()
        await cur.close()
    return [CafeOrder(*row) for row in rows]


async def fetch_order_items(db_path: str, order_id: int) -> list[dict[str, Any]]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT oi.menu_item_id, mi.title, oi.qty, oi.item_price_cents, oi.comment
            FROM cafe_order_item oi
            LEFT JOIN menu_item mi ON mi.id = oi.menu_item_id
            WHERE oi.order_id = ?
            ORDER BY oi.id
            """,
            (int(order_id),),
        )
        rows = await cur.fetchall()
        await cur.close()

    items: list[dict[str, Any]] = []
    for menu_item_id, title, qty, item_price_cents, comment in rows:
        items.append(
            {
                "menu_item_id": int(menu_item_id),
                "title": str(title) if title else f"#{menu_item_id}",
                "qty": int(qty),
                "item_price_cents": int(item_price_cents),
                "comment": str(comment or ""),
            }
        )
    return items


async def update_order_status(db_path: str, order_id: int, status: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE cafe_order SET status = ? WHERE id = ?",
            (str(status), int(order_id)),
        )
        await db.commit()


async def fetch_recent_reservations(db_path: str, *, limit: int = 20) -> list[Reservation]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT r.id, r.user_id, r.table_id, t.code, r.start_at, r.end_at, r.guests, r.name, r.phone, r.status, r.created_at
            FROM reservation r
            JOIN cafe_table t ON t.id = r.table_id
            ORDER BY r.id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = await cur.fetchall()
        await cur.close()
    return [Reservation(*row) for row in rows]


async def update_reservation_status(db_path: str, reservation_id: int, status: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE reservation SET status = ? WHERE id = ?",
            (str(status), int(reservation_id)),
        )
        await db.commit()
