CREATE TABLE IF NOT EXISTS menu_item (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  price_cents INTEGER NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS cafe_table (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  seats INTEGER NOT NULL,
  zone TEXT NOT NULL DEFAULT 'main',
  is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS reservation (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  table_id INTEGER NOT NULL,
  start_at TEXT NOT NULL,
  end_at TEXT NOT NULL,
  guests INTEGER NOT NULL,
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(table_id) REFERENCES cafe_table(id)
);

CREATE TABLE IF NOT EXISTS cafe_order (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  type TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  scheduled_for TEXT,
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  address TEXT,
  comment TEXT NOT NULL DEFAULT '',
  total_cents INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cafe_order_item (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  menu_item_id INTEGER NOT NULL,
  qty INTEGER NOT NULL,
  item_price_cents INTEGER NOT NULL,
  comment TEXT NOT NULL DEFAULT '',
  FOREIGN KEY(order_id) REFERENCES cafe_order(id),
  FOREIGN KEY(menu_item_id) REFERENCES menu_item(id)
);
