# Deploying to Render

This guide walks you through deploying the Runsum backend to Render's free tier.

## Prerequisites
- GitHub account with this repo pushed
- Render account (free) at https://render.com
- Oracle wallet files (locally, NOT in git)

## Step 1: Create Web Service on Render

1. Go to https://dashboard.render.com
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `runsum-backend` (or your choice)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app`
   - **Instance Type**: `Free`

## Step 2: Upload Wallet Files as Secret Files

1. In your Render service dashboard, go to **Environment** → **Secret Files**
2. Click **Add Secret File** for each wallet file:

   **File 1:**
   - Filename: `cwallet.sso`
   - Contents: Upload `wallet/cwallet.sso` from your local machine
   - Path: `/etc/secrets/wallet/cwallet.sso`

   **File 2:**
   - Filename: `sqlnet.ora`
   - Contents: Upload `wallet/sqlnet.ora`
   - Path: `/etc/secrets/wallet/sqlnet.ora`

   **File 3:**
   - Filename: `tnsnames.ora`
   - Contents: Upload `wallet/tnsnames.ora`
   - Path: `/etc/secrets/wallet/tnsnames.ora`

   **File 4:**
   - Filename: `ojdbc.properties`
   - Contents: Upload `wallet/ojdbc.properties`
   - Path: `/etc/secrets/wallet/ojdbc.properties`

   **File 5 (if you have it):**
   - Filename: `keystore.jks`
   - Contents: Upload `wallet/keystore.jks`
   - Path: `/etc/secrets/wallet/keystore.jks`

   **File 6 (if you have it):**
   - Filename: `truststore.jks`
   - Contents: Upload `wallet/truststore.jks`
   - Path: `/etc/secrets/wallet/truststore.jks`

## Step 3: Set Environment Variables

In **Environment** → **Environment Variables**, add:

```
CLIENT_ID=your_strava_client_id
CLIENT_SECRET=your_strava_client_secret
FRONTEND_URL=https://your-frontend-url.com
SECURE=true
JWT_SECRET=your_jwt_secret_key
ORACLE_USER=ADMIN
ORACLE_PASSWORD=your_oracle_password
WALLET_PASSWORD=your_wallet_password
```

**Important:** Make sure `FRONTEND_URL` matches your actual frontend domain!

## Step 4: Deploy

1. Click **Create Web Service**
2. Render will automatically build and deploy your app
3. Watch the logs for any errors
4. Your app will be available at: `https://runsum-backend.onrender.com` (or your chosen name)

## Step 5: Keep It Awake (Optional)

The free tier spins down after 15 minutes of inactivity. To prevent this:

1. Go to https://uptimerobot.com (free account)
2. Create a new monitor:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: Runsum Backend
   - **URL**: `https://your-app.onrender.com/health`
   - **Monitoring Interval**: 5 minutes
3. Save - your app will now stay awake!

## Testing Your Deployment

1. Visit `https://your-app.onrender.com/health` - should return `{"status": "ok"}`
2. Test your auth flow from your frontend
3. Check Render logs for any errors

## Troubleshooting

### "Error connecting to database"
- Check that all wallet files are uploaded correctly
- Verify `ORACLE_PASSWORD` and `WALLET_PASSWORD` are correct
- Check that the paths in Secret Files are `/etc/secrets/wallet/filename`

### "ModuleNotFoundError"
- Make sure `requirements.txt` is up to date
- Check Render build logs for installation errors

### CORS Errors
- Verify `FRONTEND_URL` environment variable matches your frontend domain exactly
- Make sure `SECURE=true` if using HTTPS

## Updating Your App

Just push to GitHub! Render will automatically:
1. Detect the push
2. Rebuild your app
3. Deploy the new version
4. Zero downtime swap

## Monitoring

- **Logs**: View real-time logs in Render dashboard
- **Metrics**: See CPU/RAM usage in Render dashboard
- **Alerts**: Set up UptimeRobot to email you if the app goes down

---

Your app is now live! 🚀

