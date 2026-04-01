# Deploy frePPLe on Render (Free Tier)

Yes, you can deploy frePPLe on Render's free tier. Here's how.

## Free Tier Limitations

| Resource | Free Tier |
|----------|-----------|
| Web Service | 512MB RAM, spins down after 15 min inactivity |
| PostgreSQL | 90 days free, 1GB storage |
| Build time | 4000 min/month |
| Cold start | ~30-60 seconds after inactivity |

**Note:** The first build may take **15-25 minutes** due to C++ compilation. Subsequent builds are faster with Docker layer caching.

---

## Option A: One-Click Deploy (Blueprint)

1. **Push your code to GitHub** (if not already)

2. **Go to [Render Dashboard](https://dashboard.render.com)** → **New** → **Blueprint**

3. **Connect your GitHub repo** and select this repository

4. **Render will detect `render.yaml`** and create:
   - A PostgreSQL database (frepple-db)
   - A Web Service (frepple) from your Dockerfile

5. **Click "Apply"** and wait for the build to complete

---

## Option B: Manual Setup

### Step 1: Create a Render Account
- Sign up at [render.com](https://render.com) (free)

### Step 2: Create PostgreSQL Database
1. **Dashboard** → **New** → **PostgreSQL**
2. Name: `frepple-db`
3. Plan: **Free**
4. Region: Choose closest to you
5. Click **Create Database**
6. Wait for it to be ready, then note the **Internal Database URL** or individual values (host, user, password, etc.)

### Step 3: Create Web Service
1. **Dashboard** → **New** → **Web Service**
2. **Connect your GitHub repository** (authorize Render if needed)
3. Select this repository
4. Configure:
   - **Name:** `frepple` (or any name)
   - **Region:** Same as your database
   - **Branch:** `main` (or your default branch)
   - **Runtime:** **Docker**
   - **Plan:** **Free**

### Step 4: Environment Variables
Add these in the **Environment** section (use values from your PostgreSQL):

| Key | Value | Example |
|-----|-------|---------|
| `POSTGRES_HOST` | Your DB host | `dpg-xxxxx-a.oregon-postgres.render.com` |
| `POSTGRES_PORT` | `5432` | `5432` |
| `POSTGRES_USER` | Your DB user | `frepple` |
| `POSTGRES_PASSWORD` | Your DB password | (from Render) |
| `POSTGRES_DBNAME` | Your DB name | `frepple` |

**Tip:** If your Render PostgreSQL shows "Internal Database URL", use the hostname from it for `POSTGRES_HOST`. Render provides an "Internal" URL for services in the same region (faster, no connection limit).

### Step 5: Deploy
- Click **Create Web Service**
- Render will build your Docker image (15-25 min first time)
- Once deployed, you'll get a URL like `https://frepple-xxxx.onrender.com`

### Step 6: Create Admin User (First Time)
After the first deploy, open the **Shell** tab in your Render service and run:
```bash
frepplectl createsuperuser
```
Follow the prompts to create an admin account.

---

## Troubleshooting

**Build fails?**
- Check build logs for errors
- Ensure all files are committed (including `docker-entrypoint.sh`, `djangosettings.py`)
- Free tier has 512MB - if build runs out of memory, consider using Render's paid build (or build locally and push to Docker Hub)

**App won't start?**
- Verify all `POSTGRES_*` env vars are set correctly
- Check that you're using the **Internal** database host (not external) for same-region services

**Cold starts?**
- Free tier spins down after 15 min of no traffic
- First request after spin-down takes 30-60 seconds
- Upgrade to paid ($7/mo) for always-on
