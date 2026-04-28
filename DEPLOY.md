# Cloud deploy — Supabase + Streamlit Community Cloud

Splits the dataset between **local 100k SQLite** (full fidelity, 2.8 GB) and a
**cloud 10k Postgres** (~290 MB SQLite source → ~350 MB Postgres after import,
fits Supabase free 500 MB tier).

## 0. One-time accounts

| | URL | Notes |
|---|---|---|
| Supabase  | https://supabase.com         | Free tier: 500 MB DB, 5 GB egress |
| Streamlit | https://streamlit.io/cloud   | Free tier: public repos only      |
| GitHub    | https://github.com           | (Already authed in this repo)     |

## 1. Create the Supabase project

1. supabase.com → **New project** → name `kreditueberwachung`, region close to
   you (e.g. `eu-central-1`), set a strong password.
2. Wait for provisioning (~1 min).
3. **Project Settings → Database → Connection string → URI** → copy the
   *Transaction pooler* URI (port 6543). Paste the password into the URI.

## 2. Migrate the demo data

The 10k demo dataset already lives at `output_demo/kreditueberwachung.db`.
If you want to regenerate it:

```bash
KU_OUTPUT_DIR=output_demo KU_N_CLIENTS=10000 .venv/bin/python scripts/generate.py
KU_OUTPUT_DIR=output_demo .venv/bin/python scripts/run_stress.py --scenario all
```

Then run the migration. Use the **Session pooler URI (port 5432)** for the
migration (transaction pooler doesn't support `DROP TABLE … CASCADE` reliably):

```bash
DATABASE_URL='postgresql://postgres.<ref>:<pwd>@aws-0-eu-central-1.pooler.supabase.com:5432/postgres' \
SOURCE_SQLITE=output_demo/kreditueberwachung.db \
.venv/bin/python scripts/migrate_to_postgres.py
```

Expect ~3-5 minutes. Verify in Supabase **SQL editor**:

```sql
SELECT 'client', COUNT(*) FROM client UNION ALL
SELECT 'loan',   COUNT(*) FROM loan   UNION ALL
SELECT 'event',  COUNT(*) FROM event;
```

## 3. Push code to GitHub

```bash
gh repo create kreditueberwachung-cockpit --private --source=. --remote=origin --push
```

Or, if a public repo (required for Streamlit Cloud free):

```bash
gh repo create kreditueberwachung-cockpit --public --source=. --remote=origin --push
```

## 4. Deploy on Streamlit Community Cloud

1. https://share.streamlit.io → **New app**
2. Repository: `philipp-collab/kreditueberwachung-cockpit`
3. Branch: `main`
4. **Main file path**: `dashboard/app.py`
5. Python version: 3.11 (or 3.12)
6. Click **Advanced settings → Secrets** and paste:

```toml
[database]
url = "postgresql://postgres.<ref>:<pwd>@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
```

   (use the **Transaction pooler** here — port 6543, better for short HTTP
   request lifecycles)

7. **Deploy**.

The first build pulls all `requirements.txt` deps (~2 min). After that it's
hot-reload on every git push.

## 5. Stable URL

The Streamlit Cloud URL is stable per app; pattern:

    https://<your-handle>-kreditueberwachung-cockpit-<hash>.streamlit.app

You can claim a custom subdomain in the app's settings.

## Switch to full 100k later

If you upgrade Supabase to Pro (~$25/mo, 8 GB DB), re-run the migration with the
full SQLite source:

```bash
SOURCE_SQLITE=output/kreditueberwachung.db \
DATABASE_URL='…session pooler…' \
.venv/bin/python scripts/migrate_to_postgres.py
```

## Local-only mode

If `DATABASE_URL` and `st.secrets["database"]["url"]` are both missing, the app
falls back to the local SQLite at `output/kreditueberwachung.db` — useful for
development and to keep working with the full 100k dataset locally.
