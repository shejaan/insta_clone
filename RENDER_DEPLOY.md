# Deploying to Render — Step-by-Step Guide

## Prerequisites

- A [Render](https://render.com) account (free tier works)
- A [Cloudinary](https://cloudinary.com) account (free tier — for media file storage)
- Your project pushed to a **GitHub** or **GitLab** repository

---

## 1. Environment Variables

On Render → your Web Service → **Environment** tab, add:

| Key | Value | Description |
|-----|-------|-------------|
| `SECRET_KEY` | `your-very-long-random-secret-key` | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` | Always `False` in production |
| `ALLOWED_HOSTS` | `yourapp.onrender.com` | Comma-separated if you have a custom domain |
| `DATABASE_URL` | *(set automatically by Render PostgreSQL add-on)* | See Step 3 |
| `CLOUDINARY_URL` | `cloudinary://api_key:api_secret@cloud_name` | Get from Cloudinary dashboard |

> **Never** put real secrets in `.env` and commit them to Git. Use Render's env panel only.

---

## 2. Verify `build.sh`

Your `build.sh` at project root should look like this:

```bash
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
```

Make it executable before committing:
```powershell
# On Windows (Git Bash):
chmod +x build.sh
git add build.sh
git commit -m "Make build.sh executable"
```

---

## 3. PostgreSQL Database on Render

1. In Render dashboard → **New** → **PostgreSQL**
2. Choose free tier, pick a region
3. After it creates, copy the **Internal Database URL**
4. Add it as `DATABASE_URL` env var in your Web Service

> Render automatically injects `DATABASE_URL` if you link the database to the Web Service from the service settings.

---

## 4. Web Service Configuration

| Field | Value |
|-------|-------|
| **Build Command** | `./build.sh` |
| **Start Command** | `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120` |
| **Environment** | `Python 3` |
| **Instance Type** | Free (or Starter for better performance) |
| **Root Directory** | *(leave empty)* |

---

## 5. `requirements.txt` — Required Packages

Make sure these are included:

```
django>=4.2
gunicorn
whitenoise[brotli]
dj-database-url
psycopg2-binary
python-dotenv
cloudinary
django-cloudinary-storage
Pillow
```

Update if needed:
```powershell
pip freeze > requirements.txt
```

---

## 6. Deployment Flow

```
Git Push → Render auto-detects → Runs build.sh → Starts Gunicorn
```

1. Push your code to GitHub
2. On Render, connect the repo → Deploy
3. Watch the logs for errors
4. Visit your `.onrender.com` URL

---

## 7. Common Issues & Fixes

### `DisallowedHost` error
→ Add your Render URL to `ALLOWED_HOSTS` env var.
```
ALLOWED_HOSTS=myapp.onrender.com
```

### Static files 404 (CSS/JS not loading)
→ `collectstatic` must run in `build.sh`. WhiteNoise serves static files automatically.

### Media files 404 (uploaded images missing)
→ Set `CLOUDINARY_URL` env var. Render's filesystem is ephemeral — all uploads are lost on redeploy without Cloudinary.

### Migration errors on deploy
→ **Always** include `python manage.py migrate` in `build.sh`. Render runs this on every deploy.

### `CSRF verification failed` on POST requests
→ Make sure `CSRF_TRUSTED_ORIGINS` in settings.py includes your Render domain. This is handled automatically since `settings.py` reads `ALLOWED_HOSTS` to build it.

### `psycopg2` not found
→ Add `psycopg2-binary` to `requirements.txt`.

### `502 Bad Gateway`
→ Check gunicorn worker count. Under free tier, use `--workers 1`.

---

## 8. Cloudinary Setup

1. Log in to [cloudinary.com](https://cloudinary.com)
2. Dashboard → copy your **API Environment variable**: `cloudinary://...`
3. Paste it as the `CLOUDINARY_URL` env var on Render
4. All new uploads will go directly to Cloudinary

> **Existing local uploads in `/media/`** will NOT be migrated automatically.
> You'll need to re-upload them or use the Cloudinary bulk upload tool.

---

## 9. Post-Deployment Checklist

- [ ] Visit your `.onrender.com` URL — site loads ✅
- [ ] Register a new user — profile auto-created ✅  
- [ ] Upload a post — image serves from Cloudinary URL ✅  
- [ ] Check Django admin at `/admin/` ✅
- [ ] Run `python manage.py createsuperuser` via Render Shell for admin access

---

## 10. Render Shell (for one-off commands)

In Render → your Web Service → **Shell** tab:
```bash
python manage.py createsuperuser
python manage.py migrate
python manage.py collectstatic --no-input
```
