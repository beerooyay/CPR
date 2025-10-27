#!/bin/bash

# Firebase Functions Setup Script for CPR-NFL
# This script sets up and deploys Firebase Functions

set -e

echo "🔥 CPR-NFL Firebase Functions Setup"
echo "===================================="

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    echo "❌ Firebase CLI not found. Installing..."
    npm install -g firebase-tools
else
    echo "✅ Firebase CLI found"
fi

# Check if user is logged in
if ! firebase login:list | grep -q "active"; then
    echo "🔐 Please login to Firebase:"
    firebase login
else
    echo "✅ Already logged in to Firebase"
fi

# Navigate to functions directory
cd functions

# Install dependencies
echo "📦 Installing Firebase Functions dependencies..."
npm install

# Build TypeScript
echo "🔨 Building TypeScript..."
npm run build

# Check if Firebase project is set
if [ ! -f ".firebaserc" ]; then
    echo "📋 Please set your Firebase project:"
    echo "   firebase use your-project-id"
    echo "   Then run this script again"
    exit 1
else
    echo "✅ Firebase project configured"
fi

# Test locally (optional)
read -p "🧪 Test functions locally? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting local emulator..."
    npm run serve
fi

# Deploy to production
read -p "🚀 Deploy to Firebase? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🌐 Deploying Firebase Functions..."
    npm run deploy
    
    echo "🌐 Deploying web hosting..."
    cd ..
    firebase deploy --only hosting
    
    echo "✅ Deployment complete!"
    echo ""
    echo "📊 Your API endpoints are available at:"
    echo "   - Health: https://us-central1-$(firebase apps:list | grep 'Web App' | awk '{print $4}' | head -1).cloudfunctions.net/health"
    echo "   - Rankings: https://us-central1-$(firebase apps:list | grep 'Web App' | awk '{print $4}' | head -1).cloudfunctions.net/rankings"
    echo ""
    echo "🌐 Your web app is available at:"
    echo "   - https://$(firebase apps:list | grep 'Web App' | awk '{print $4}' | head -1).web.app"
else
    echo "💡 To deploy later, run:"
    echo "   cd functions && npm run deploy"
    echo "   cd .. && firebase deploy --only hosting"
fi

echo ""
echo "🎉 Firebase Functions setup complete!"
