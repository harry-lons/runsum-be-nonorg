# Deploying to Render

This guide walks you through deploying the Runsum backend to Render's free tier.

## Prerequisites
- GitHub account with this repo pushed
- Render account (free) at https://render.com
- Oracle Autonomous Database configured for TLS (not mTLS)

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

## Step 2: Set Environment Variables

In **Environment** → **Environment Variables**, add:

```
CLIENT_ID=your_strava_client_id
CLIENT_SECRET=your_strava_client_secret
FRONTEND_URL=https://your-frontend-url.com
SECURE=true
JWT_SECRET=your_jwt_secret_key
ORACLE_USER=ADMIN
ORACLE_PASSWORD=your_oracle_password
ORACLE_DSN=(description= (retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.us-sanjose-1.oraclecloud.com))(connect_data=(service_name=gb4d36291b4e17a_runsum_high.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))
```

**Note:** Database now uses TLS (one-way) mode - no wallet files needed!

**Important:** Make sure `FRONTEND_URL` matches your actual frontend domain!

## Step 3: Deploy

1. Click **Create Web Service**
2. Render will automatically build and deploy your app
3. Watch the logs for any errors
4. Your app will be available at: `https://runsum-backend.onrender.com` (or your chosen name)

## Step 4: Keep It Awake (Optional)

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
- Verify `ORACLE_USER` and `ORACLE_PASSWORD` are correct
- Check that `ORACLE_DSN` is properly formatted and matches your database
- Ensure your Oracle database is configured for TLS (not mTLS) access

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

