# ForceHub Bot — Vercel Deployment Guide

## ⚠️ Important: Vercel vs Railway

| Feature          | Vercel              | Railway ✅ Recommended |
|------------------|---------------------|------------------------|
| Bot mode         | Webhook (serverless)| Polling (always-on)    |
| Data persistence | ❌ Resets on redeploy| ✅ Persistent volume   |
| Free tier        | Generous            | $5/month after trial   |
| Setup complexity | Medium              | Simple                 |

**If data persistence matters, use Railway.**  
Vercel's filesystem is ephemeral — bot data resets every redeploy.

---

## Files

```
forcehub/
├── app.py           ← Vercel entrypoint (Flask webhook handler)
├── bot.py           ← All bot logic (unchanged)
├── vercel.json      ← Vercel build + routing config
├── requirements.txt ← Dependencies (includes Flask)
├── .env.example     ← Environment variable template
└── README.md        ← This file
```

---

## Step-by-Step Deploy

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "ForceHub Bot"
git remote add origin https://github.com/yourusername/forcehub-bot
git push -u origin main
```

### 2. Deploy on Vercel
- Go to [vercel.com](https://vercel.com) → New Project
- Import your GitHub repo
- Framework: **Other**
- Root directory: `.` (leave default)

### 3. Set Environment Variables
In Vercel Dashboard → Your Project → Settings → Environment Variables:

| Name          | Value                                        |
|---------------|----------------------------------------------|
| `BOT_TOKEN`   | Your bot token from @BotFather               |
| `ADMIN_IDS`   | `5695957392` (your Telegram ID)              |
| `WEBHOOK_URL` | Leave blank for now (set after first deploy) |
| `DATA_DIR`    | `/tmp`                                       |

### 4. Deploy
Click **Deploy**. Wait for it to finish.

### 5. Set WEBHOOK_URL
After deploy, copy your Vercel URL (e.g. `https://forcehub-abc.vercel.app`)

Go back to Environment Variables → Add:
- `WEBHOOK_URL` = `https://forcehub-abc.vercel.app`

Redeploy once more (Vercel Dashboard → Deployments → Redeploy).

### 6. Register Webhook with Telegram
Open this URL in your browser:
```
https://your-app.vercel.app/set_webhook
```

You should see:
```json
{"set_webhook": true, "url": "https://your-app.vercel.app/webhook"}
```

✅ **Your bot is now live!**

---

## Health Check
Visit `https://your-app.vercel.app/` to see:
```json
{
  "status": "ok",
  "bot": "ForceHub",
  "users": 0,
  "creators": 0,
  "campaigns": 0
}
```

---

## Switching back to Railway / Polling
Before switching, delete the webhook:
```
https://your-app.vercel.app/delete_webhook
```
Then redeploy on Railway using the original `bot.py` directly.

---

## Troubleshooting

**Bot not responding:**
- Check that you visited `/set_webhook` after deploy
- Verify `BOT_TOKEN` is correct in Vercel env vars
- Check Vercel function logs (Dashboard → Functions tab)

**Data lost after redeploy:**
- Expected on Vercel — use Railway for persistent storage
- Or connect an external database (PlanetScale, Supabase, etc.)

**Timeout errors:**
- Vercel free tier has 10s function timeout
- Pro tier has 60s
- Heavy broadcasts may timeout — Railway is better for this
