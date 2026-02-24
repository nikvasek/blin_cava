# blin_cava — Telegram Mini App + bot receiver

Mini App (Telegram WebApp) for cafe menu + cart + delivery checkout. The Telegram bot is a thin shell: it opens the Mini App and receives completed orders via `web_app_data`, then stores them in SQLite.

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

Open `.env` and set:

- `BOT_TOKEN`
- `WEBAPP_URL` (must be **https**, e.g. GitHub Pages URL)

Optional:

- `ADMIN_CHAT_ID` — if set, the bot notifies this chat about new orders.

3) Run:

```bash
python main.py
```

## Data

- SQLite DB file: `data/cafe.db`
- Backup script: `scripts/backup_db.sh`

## Apply menu from reference

If you already have `data/cafe.db` and want to update the active menu to the reference menu preset:

```bash
python scripts/apply_reference_menu.py
```

It deactivates previous menu items (keeps them in DB for historical orders) and activates/updates the reference items.

## Telegram Mini App (WebApp)

This repo includes a minimal WebApp in `webapp/` (menu → cart → delivery → send to bot).

1) Host `webapp/` somewhere with **HTTPS** (required by Telegram WebApps).
	- Free options: GitHub Pages / Netlify / Vercel.
	- For local dev: use a tunnel (ngrok / Cloudflare Tunnel) to get an https URL.

2) Put the public URL into `.env` as `WEBAPP_URL` and restart the bot.

3) In Telegram, run `/start` or `/app`.

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


