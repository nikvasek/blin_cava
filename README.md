# blin_cava — Telegram bot (MVP skeleton)

Minimal skeleton for a cafe Telegram bot: menu browsing, order flow (delivery/pickup), and table reservations with real table list + optional hall plan image.

## Quick start (macOS)

1) Create venv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Configure environment:

```bash
cp .env.example .env
```

Open `.env` and set `BOT_TOKEN`.

3) Run:

```bash
python main.py
```

## Data

- SQLite DB file: `data/cafe.db`
- Backup script: `scripts/backup_db.sh`

Put your hall plan image (PNG/JPG) into `assets/hall_plan.png` (optional). If the file is missing, the bot will still work.

## Apply menu from reference

If you already have `data/cafe.db` and want to update the active menu to the reference menu preset:

```bash
python scripts/apply_reference_menu.py
```

It deactivates previous menu items (keeps them in DB for historical orders) and activates/updates the reference items.

## Telegram Mini App (WebApp)

This repo includes a minimal WebApp in `webapp/` (menu + cart + "Send to bot").

1) Host `webapp/` somewhere with **HTTPS** (required by Telegram WebApps).
	- Free options: GitHub Pages / Netlify / Vercel.
	- For local dev: use a tunnel (ngrok / Cloudflare Tunnel) to get an https URL.

2) Put the public URL to `webapp/index.html` into `.env` as `WEBAPP_URL` and restart the bot.

3) In Telegram, press **📱 Мини‑приложение** or run `/app`.

### GitHub Pages (free) quick start

This repo already includes a ready-to-publish folder: `docs/`.

1) Push the project to GitHub.
2) In GitHub open **Settings → Pages**.
3) **Build and deployment** → **Source**: “Deploy from a branch”.
4) Select **Branch**: `main` and **Folder**: `/docs`.
5) Wait until GitHub shows your site URL.

Then set in `.env`:

`WEBAPP_URL=https://<username>.github.io/<repo>/`

and restart the bot.

## Admin: edit menu prices

1) Put your Telegram user id into `.env` as `ADMIN_USER_IDS` (comma-separated).
2) In Telegram send `/admin` to the bot.
3) Select a menu item → **✏️ Изменить цену** → send a number like `930`.

## Admin: view orders and bookings

- `/orders` — shows last 20 orders, opens details, lets you change order status.
- `/bookings` — shows last 20 table reservations, opens details, lets you change reservation status.

## Admin: command list

- `/admin_help` — prints all bot commands with short explanations (also available as a keyboard button **🛠 Админ команды** for admins).
