# Firebase Cloud Setup - NO LOCAL SERVER NEEDED! 🚀

## Setup OpenRouter in Firebase (5 minutes)

### 1. Install Firebase Functions Dependencies
```bash
cd functions
npm install
```

### 2. Set Your OpenRouter API Key in Firebase
```bash
# Set the config (this stores it encrypted in Google Cloud)
firebase functions:config:set openrouter.api_key="sk-or-v1-your_actual_key_here"

# Optional: Set ESPN League ID too
firebase functions:config:set espn.league_id="your_league_id"
```

### 3. Deploy the Cloud Function
```bash
# Deploy just the chat proxy function
firebase deploy --only functions:chatProxy

# Or deploy all functions
firebase deploy --only functions
```

### 4. That's it! 
Your chat feature now works **100% in the cloud**. No local server needed!

## How It Works

```
Your Browser (app.js)
    ↓ [no API keys]
Firebase Cloud Function (runs in Google Cloud)
    ↓ [secure API key storage]
OpenRouter API
    ↓
AI Response
```

## Testing

1. Open your web app (locally or deployed)
2. Click any "GET SCOUTING REPORT" button
3. Chat works without any local server running!

## View Your Function URL

After deployment, you'll see:
```
Function URL (chatProxy): https://us-central1-cpr-app-54c15.cloudfunctions.net/chatProxy
```

This is already configured in your `app.js` file.

## Check Logs

```bash
firebase functions:log --only chatProxy
```

## Update API Key Later

```bash
# Change the key anytime
firebase functions:config:set openrouter.api_key="new_key_here"

# Redeploy to apply changes
firebase deploy --only functions:chatProxy
```

## Cost

- Cloud Functions free tier: 2 million invocations/month
- You'll never hit this with normal usage
- OpenRouter costs are separate (but Llama 3.2 is free!)

---

**NO LOCAL SERVER NEEDED - FULLY CLOUD BASED!** 🌩️
