# Render Deployment Guide — Instagram Clone

Complete step-by-step guide to deploy this Django app on Render with PostgreSQL and Cloudinary.

---

## Prerequisites

- [Render account](https://render.com)
- [Cloudinary account](https://cloudinary.com) (free tier is fine)
- Your code pushed to GitHub

---

## Step 1: Create a PostgreSQL Database on Render

1. Go to **Render Dashboard → New → PostgreSQL**
2. Choose a name (e.g., `instaclone-db`) and region
3. Click **Create Database**
4. Copy the **Internal Database URL** — you'll need it as `DATABASE_URL`

---

## Step 2: Get Your Cloudinary URL

1. Log in to [Cloudinary Dashboard](https://console.cloudinary.com)
2. Go to **Dashboard → API Keys**
3. Copy the **API Environment variable** — it looks like:
   ```
   cloudinary://API_KEY:API_SECRET@CLOUD_NAME
   ```
4. This is your `CLOUDINARY_URL` value

---

## Step 3: Create a Web Service on Render

1. Go to **Render Dashboard → New → Web Service**
2. Connect your GitHub repository
3. Set the following:

   | Field | Value |
   |---|---|
   | **Runtime** | Python 3 |
   | **Build Command** | `./build.sh` |
   | **Start Command** | `gunicorn config.wsgi:application` |

---

## Step 4: Set Environment Variables

In your Render Web Service → **Environment** tab, add:

| Variable | Value | Notes |
|---|---|---|
| `SECRET_KEY` | Random 50-char string | Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` | Must be `False` in production |
| `ALLOWED_HOSTS` | `yourapp.onrender.com` | Your Render domain (no `https://`) |
| `DATABASE_URL` | From Render PostgreSQL dashboard | Use the **Internal** URL |
| `CLOUDINARY_URL` | `cloudinary://key:secret@cloud_name` | From Cloudinary dashboard |
| `DJANGO_SUPERUSER_USERNAME` | `admin` | Used to auto-create admin account |
| `DJANGO_SUPERUSER_EMAIL` | `admin@example.com` | Admin email |
| `DJANGO_SUPERUSER_PASSWORD` | Strong password | Admin login password |

> **Important**: `ALLOWED_HOSTS` must be set or the app will raise `ImproperlyConfigured` and fail to start.

> **Important**: `CLOUDINARY_URL` must be set or media uploads will be lost on every redeploy (Render uses an ephemeral filesystem).

---

## Step 5: Deploy

1. Click **Deploy** (or push to GitHub to trigger auto-deploy)
2. Watch the build logs — you should see:
   ```
   ==> Installing Python dependencies...
   ==> Collecting static files...
   ==> Running database migrations...
   ==> Creating superuser if not present...
   Superuser "admin" created successfully.
   ==> Build complete!
   ```

---

## Step 6: Access the Admin Panel

1. Go to: `https://yourapp.onrender.com/admin/`
2. Log in with the credentials you set in `DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD`
3. Admin CSS/JS loads from WhiteNoise (static files collected at build time) ✅

### If Admin CSS is Broken (Troubleshooting)

This happens if `collectstatic` failed during build. Check:

1. Build logs for any errors mentioning `collectstatic`
2. Ensure `CLOUDINARY_URL` is set correctly (malformed URL causes import errors)
3. Re-deploy to re-run `collectstatic --clear`

---

## Step 7: Adding a Custom Domain (Optional)

1. In Render → Web Service → **Settings → Custom Domains**
2. Add your domain (e.g., `www.mysite.com`)
3. Update `ALLOWED_HOSTS` to include both:
   ```
   yourapp.onrender.com,www.mysite.com
   ```
4. Update `CSRF_TRUSTED_ORIGINS` is auto-generated from `ALLOWED_HOSTS` in settings ✅

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Django secret key. Use a 50+ char random string. Never use the default. |
| `DEBUG` | ✅ | Set to `False` in production |
| `ALLOWED_HOSTS` | ✅ | Comma-separated host names. App raises `ImproperlyConfigured` if empty in production. |
| `DATABASE_URL` | ✅ | PostgreSQL connection string from Render |
| `CLOUDINARY_URL` | ✅ | Cloudinary API URL. Without this, media files are lost on redeploy. |
| `DJANGO_SUPERUSER_USERNAME` | Recommended | Auto-creates admin on first deploy |
| `DJANGO_SUPERUSER_EMAIL` | Recommended | Admin email |
| `DJANGO_SUPERUSER_PASSWORD` | Recommended | Admin password |

---

## Useful Commands (Render Shell)

Access via Render Dashboard → Web Service → **Shell** tab:

```bash
# Create superuser manually
python manage.py createsuperuser

# Check deployment configuration
python manage.py check --deploy

# Apply any pending migrations
python manage.py migrate

# View all registered URL patterns
python manage.py show_urls  # (requires django-extensions)
```

---

## Media File Persistence

Media files (profile pictures, post images) are stored on **Cloudinary** in production.

- Files are **never stored on Render's filesystem** in production ✅
- Cloudinary free tier gives 25GB storage and 25GB monthly bandwidth
- Uploaded files survive all redeployments ✅

**If `CLOUDINARY_URL` is missing**: The app will log a `CRITICAL` warning and fall back to local storage — files will be lost on the next redeploy.

---

## Checklist Before Going Live

- [ ] `DEBUG=False` set in environment
- [ ] `SECRET_KEY` is random and secret (not the Django default)
- [ ] `ALLOWED_HOSTS` set to your Render domain
- [ ] `DATABASE_URL` connected to Render PostgreSQL
- [ ] `CLOUDINARY_URL` set from your Cloudinary dashboard
- [ ] Superuser created (either via env vars or `createsuperuser`)
- [ ] Admin panel accessible at `/admin/`
- [ ] Test: upload a post image → redeploy → image still visible ✅
