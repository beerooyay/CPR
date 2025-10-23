# Firebase Setup Guide for CPR v2.0 🔥

## Why Firebase?
- **No backend code needed** for auth
- **Free tier**: 10k/month sign-ins (plenty for your league)
- **Google, Discord, Email** all built-in
- **Firestore**: Save chat history, user preferences
- **Real-time updates**: Live CPR scores across devices

---

## Step 1: Create Firebase Project (5 minutes)

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click "Add project"
3. Name it: `CPR-FBA-League` (or whatever)
4. **Disable Google Analytics** (unless you want it)
5. Click "Create Project"

---

## Step 2: Register Your Web App (2 minutes)

1. In Firebase Console, click the **</>** (Web) icon
2. App nickname: `CPR Web App`
3. **Check** "Also set up Firebase Hosting" (optional but cool)
4. Click "Register app"
5. **COPY THE CONFIG** - you'll need this! Should look like:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  authDomain: "cpr-fba-league.firebaseapp.com",
  projectId: "cpr-fba-league",
  storageBucket: "cpr-fba-league.firebasestorage.app",
  messagingSenderId: "123456789012",
  appId: "1:123456789012:web:abcdef1234567890"
};
```

6. Click "Continue to console"

---

## Step 3: Enable Authentication Providers (3 minutes)

1. In Firebase Console sidebar → **Build** → **Authentication**
2. Click "Get started"
3. Click **"Sign-in method"** tab
4. Enable these providers:

### Google (Easiest)
- Click "Google"
- Toggle **Enable**
- Select support email (your Gmail)
- Click "Save"

### Email/Password (For testing)
- Click "Email/Password"
- Toggle **Enable**
- Click "Save"

### Discord (Optional - requires Discord app)
- Click "Discord"
- Toggle Enable
- Get Client ID & Secret from [Discord Developers](https://discord.com/developers/applications)
- Add redirect: `https://cpr-fba-league.firebaseapp.com/__/auth/handler`
- Click "Save"

---

## Step 4: Set Up Firestore (Optional - for chat history)

1. Sidebar → **Build** → **Firestore Database**
2. Click "Create database"
3. Choose **Start in test mode** (we'll secure it later)
4. Select location: `us-central1` (or closest to you)
5. Click "Enable"

---

## Step 5: Add Firebase to Your App (NOW THE FUN PART)

### Option A: CDN (Easiest - What We'll Use)

Add this to your `index.html` **before** `</body>`:

```html
<!-- Firebase SDKs -->
<script type="module">
  // Import Firebase
  import { initializeApp } from 'https://www.gstatic.com/firebasejs/11.0.2/firebase-app.js';
  import { getAuth, signInWithPopup, GoogleAuthProvider, signOut, onAuthStateChanged } 
    from 'https://www.gstatic.com/firebasejs/11.0.2/firebase-auth.js';

  // Your Firebase config (REPLACE WITH YOUR CONFIG FROM STEP 2)
  const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_PROJECT.firebaseapp.com",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_PROJECT.firebasestorage.app",
    messagingSenderId: "YOUR_SENDER_ID",
    appId: "YOUR_APP_ID"
  };

  // Initialize Firebase
  const app = initializeApp(firebaseConfig);
  const auth = getAuth(app);

  // Make auth available globally
  window.firebaseAuth = auth;
  window.GoogleAuthProvider = GoogleAuthProvider;
  window.signInWithPopup = signInWithPopup;
  window.signOut = signOut;
  window.onAuthStateChanged = onAuthStateChanged;

  console.log('🔥 Firebase initialized!');
</script>
```

### Option B: npm (If using bundler)

```bash
npm install firebase
```

```javascript
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
```

---

## Step 6: Update Your JavaScript Functions

Replace the placeholder functions in `app.js`:

```javascript
// Google Sign-In
async function loginGoogle() {
    try {
        const provider = new window.GoogleAuthProvider();
        const result = await window.signInWithPopup(window.firebaseAuth, provider);
        
        const user = result.user;
        console.log('✓ Signed in:', user.displayName);
        
        // Update UI
        document.getElementById('auth-status').innerHTML = 
            `<p style="color: #4ade80;">✓ Signed in as ${user.displayName}</p>`;
        
        closeProfile();
    } catch (error) {
        console.error('Sign-in error:', error);
        alert('Sign-in failed: ' + error.message);
    }
}

// Sign Out
function logout() {
    window.signOut(window.firebaseAuth).then(() => {
        console.log('✓ Signed out');
        document.getElementById('auth-status').innerHTML = 
            '<p style="color: #66b3ff;">not connected</p>';
    });
}

// Listen for auth state changes
window.onAuthStateChanged(window.firebaseAuth, (user) => {
    if (user) {
        console.log('🔥 User logged in:', user.email);
        // Update UI to show user profile
        updateUserProfile(user);
    } else {
        console.log('❌ User logged out');
    }
});

function updateUserProfile(user) {
    // You can now access:
    // user.displayName
    // user.email
    // user.photoURL
    // user.uid
    
    // Store in localStorage or update global state
    localStorage.setItem('user_name', user.displayName);
    localStorage.setItem('user_email', user.email);
}
```

---

## Step 7: Security Rules (IMPORTANT!)

### Firestore Rules (for chat history)

Go to **Firestore Database** → **Rules** tab:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Only authenticated users can read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Chat messages - only authenticated users
    match /chat_messages/{messageId} {
      allow read: if request.auth != null;
      allow create: if request.auth != null;
      allow update, delete: if request.auth != null && 
                              request.auth.uid == resource.data.userId;
    }
  }
}
```

Click **Publish**

---

## Step 8: Add Firestore Chat History (Optional Bonus)

```javascript
import { getFirestore, collection, addDoc, query, orderBy, limit } 
  from 'https://www.gstatic.com/firebasejs/11.0.2/firebase-firestore.js';

const db = getFirestore(app);

// Save chat message
async function saveChatMessage(role, content) {
    const user = window.firebaseAuth.currentUser;
    if (!user) return;
    
    await addDoc(collection(db, 'chat_messages'), {
        userId: user.uid,
        userName: user.displayName,
        role: role,
        content: content,
        timestamp: new Date()
    });
}

// Load chat history
async function loadChatHistory() {
    const user = window.firebaseAuth.currentUser;
    if (!user) return;
    
    const q = query(
        collection(db, 'chat_messages'),
        orderBy('timestamp', 'desc'),
        limit(50)
    );
    
    const snapshot = await getDocs(q);
    snapshot.forEach(doc => {
        const msg = doc.data();
        chatMessages.push({ role: msg.role, content: msg.content });
    });
    
    renderChat();
}
```

---

## Complete Implementation Checklist

- [ ] Create Firebase project
- [ ] Register web app, copy config
- [ ] Enable Google Sign-In
- [ ] Add Firebase CDN scripts to index.html
- [ ] Replace firebaseConfig with your config
- [ ] Update loginGoogle() function
- [ ] Test sign-in (open console, click Google button)
- [ ] Add sign-out button to profile modal
- [ ] (Optional) Set up Firestore for chat history
- [ ] (Optional) Add Discord auth
- [ ] Deploy with Firebase Hosting (bonus)

---

## Testing Locally

1. Open http://localhost:5001
2. Click profile button (👤)
3. Click "GOOGLE"
4. Sign in with your Google account
5. Check browser console - should see "✓ Signed in: Your Name"

---

## Firebase Hosting (Deploy to Production)

Once you're ready to go live:

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Initialize hosting
cd /Users/beerooyay/Desktop/CPR
firebase init hosting

# Select:
# - Use existing project: cpr-fba-league
# - Public directory: web
# - Single-page app: Yes
# - Set up automatic builds: No

# Deploy
firebase deploy
```

Your app will be live at: `https://cpr-fba-league.web.app` 🚀

---

## Cost Breakdown (Free Tier)

| Service | Free Tier | Your Usage | Cost |
|---------|-----------|------------|------|
| Auth | 10k sign-ins/month | ~100/month | **FREE** |
| Firestore | 50k reads, 20k writes/day | ~1k/day | **FREE** |
| Hosting | 10GB transfer/month | ~100MB/month | **FREE** |

**Total: $0/month** (for your league size)

---

## Troubleshooting

**"Access to fetch blocked by CORS"**
- Solution: Add `http://localhost:5001` to Firebase authorized domains
- Go to Authentication → Settings → Authorized domains → Add domain

**"Firebase not defined"**
- Solution: Check that Firebase CDN scripts load before your app.js
- Open DevTools → Network tab → look for firebase-*.js files

**Sign-in popup blocked**
- Solution: Allow popups for localhost
- Or use `signInWithRedirect()` instead of `signInWithPopup()`

---

## Next Steps

1. **ESPN Integration**: Store ESPN cookies in Firestore (encrypted)
2. **Team Assignment**: Link Google account to FBA team in database
3. **Discord Bot**: Use Firebase Functions to post CPR updates
4. **Real-time**: Use Firestore listeners for live score updates

---

## Resources

- [Firebase Console](https://console.firebase.google.com)
- [Firebase Auth Docs](https://firebase.google.com/docs/auth/web/start)
- [Firestore Docs](https://firebase.google.com/docs/firestore)
- [Firebase Pricing](https://firebase.google.com/pricing)

**Time to complete: ~20 minutes**
**Difficulty: Easy AF**
**Coolness Factor: 11/10** 🔥

Let's get this league authenticated! 🏀
