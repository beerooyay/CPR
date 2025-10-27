# Firebase Functions Deployment Guide

## Overview

This guide covers deploying the CPR-NFL Firebase Functions that provide the backend API for the web application.

## Prerequisites

1. **Firebase CLI installed**
   ```bash
   npm install -g firebase-tools
   ```

2. **Firebase project created**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a new project or use existing one
   - Enable Firestore Database
   - Enable Functions

3. **Authentication configured**
   ```bash
   firebase login
   firebase projects:list
   ```

## Deployment Steps

### 1. Install Dependencies

```bash
cd functions
npm install
```

### 2. Configure Firebase

```bash
# Set your Firebase project
firebase use your-project-id

# Test locally (optional)
npm run serve
```

### 3. Deploy Functions

```bash
# Deploy all functions
npm run deploy

# Or deploy specific functions
firebase deploy --only functions
```

### 4. Deploy Web App

```bash
# Deploy hosting with API rewrites
firebase deploy --only hosting
```

## Available Functions

### API Endpoints

| Function | Method | Endpoint | Description |
|----------|--------|----------|-------------|
| `databaseContext` | GET | `/api/databaseContext` | Loads database context for AI chat |
| `leagueStats` | GET | `/api/leagueStats` | Gets league statistics and team data |
| `rankings` | GET | `/api/rankings` | Returns CPR rankings |
| `teamRoster` | GET | `/api/teamRoster` | Gets specific team roster with NIV data |
| `chat` | POST | `/api/chat` | Jaylen AI chat endpoint |
| `health` | GET | `/api/health` | Health check endpoint |

### Query Parameters

#### Common Parameters
- `league_id`: Sleeper league ID (default: `1267325171853701120`)
- `season`: NFL season (default: `2025`)

#### Endpoint-Specific Parameters

**leagueStats**
- `league_id`: League ID
- `season`: Season year

**rankings**
- `league_id`: League ID
- `season`: Season year
- `week`: Specific week (optional, defaults to latest)

**teamRoster**
- `team`: Team name (required)
- `league_id`: League ID
- `season`: Season year

**databaseContext**
- `league_id`: League ID

## Data Flow

### Web App → Firebase Functions → Firestore

```
Web App (Static Hosting)
    ↓
Firebase Functions (API Layer)
    ↓
Firestore Database (Data Storage)
```

### Function Responsibilities

1. **databaseContext**: Aggregates data for AI chat
   - Recent CPR rankings
   - Recent NIV data
   - League information

2. **leagueStats**: Provides league overview
   - League metadata
   - Team list and records
   - Basic statistics

3. **rankings**: Returns CPR power rankings
   - Sorted by CPR score
   - Includes all component indices
   - Team metadata

4. **teamRoster**: Detailed team analysis
   - Team roster with player NIV scores
   - Position breakdown
   - Performance metrics

5. **chat**: AI-powered analysis
   - Natural language processing
   - Context-aware responses
   - Trade and waiver advice

## Response Format

All functions return consistent JSON responses:

```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2025-10-26T16:30:00.000Z"
}
```

Error responses:
```json
{
  "error": true,
  "message": "Error description",
  "timestamp": "2025-10-26T16:30:00.000Z"
}
```

## Testing

### Local Testing

```bash
# Start Firebase emulators
firebase emulators:start

# Test endpoints
curl http://localhost:5001/your-project/us-central1/health
curl http://localhost:5001/your-project/us-central1/rankings?league_id=1267325171853701120
```

### Production Testing

```bash
# Test deployed functions
curl https://us-central1-your-project.cloudfunctions.net/health
curl https://us-central1-your-project.cloudfunctions.net/rankings?league_id=1267325171853701120
```

## Monitoring

### View Logs

```bash
# View all function logs
firebase functions:log

# View specific function logs
firebase functions:log --only rankings
```

### Monitor Usage

1. Go to Firebase Console → Functions
2. Monitor execution count, errors, latency
3. Set up alerts for high error rates

## Security

### CORS Configuration

All functions include CORS headers for cross-origin requests from your web app.

### Input Validation

Functions validate required parameters and return appropriate error messages.

### Rate Limiting

Consider implementing rate limiting for production usage:
```javascript
// Example rate limiting middleware
const rateLimit = require('express-rate-limit');
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});
```

## Troubleshooting

### Common Issues

1. **Functions not found**
   - Check deployment completed successfully
   - Verify function names in firebase.json

2. **CORS errors**
   - Ensure CORS is properly configured
   - Check origin headers in requests

3. **Database connection issues**
   - Verify Firestore rules allow access
   - Check Firebase Admin SDK initialization

4. **Timeout errors**
   - Increase function timeout in firebase.json
   - Optimize database queries

### Debugging

```bash
# Enable debug logging
export DEBUG_FUNCTIONS=true
firebase functions:shell
```

## Cost Optimization

### Best Practices

1. **Cold starts**: Minimize initialization time
2. **Memory usage**: Use appropriate memory allocation
3. **Database queries**: Optimize Firestore queries
4. **Caching**: Implement response caching where appropriate

### Estimated Costs

- **Free tier**: 125,000 invocations/month
- **Beyond free tier**: ~$0.40 per million invocations
- **Memory**: $0.000025/GB-second
- **Network**: $0.12/GB outbound data

## Next Steps

1. Deploy functions to production
2. Test all API endpoints
3. Set up monitoring and alerts
4. Configure custom domain (optional)
5. Implement additional security measures

## Support

- [Firebase Functions Documentation](https://firebase.google.com/docs/functions)
- [Firebase Functions Pricing](https://firebase.google.com/pricing)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)
