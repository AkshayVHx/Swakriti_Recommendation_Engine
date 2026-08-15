# Voice Input Troubleshooting Guide

## Problem
Voice is showing "Listening — say your answer, or tap an option below" but the microphone isn't capturing audio.

## Quick Fixes (Try These First)

### 1. Check Microphone Permission
1. Open the app and click "🎤 Enable voice for this session"
2. A browser prompt should appear asking for microphone permission
3. **If no prompt appears**: The site might be blocked from using microphone
   - Click the lock icon in the address bar
   - Find "Microphone" setting
   - Change from "Block" to "Allow"
   - Refresh the page and try again

### 2. Open Browser Console to See Detailed Logs
1. Press **F12** to open Developer Tools
2. Click the **Console** tab
3. Perform these steps:
   - Refresh the page
   - Click "🎤 Enable voice for this session"
   - Speak something clearly into the microphone
4. You'll see logs starting with `[voice]` - these will tell you exactly what's failing

## Expected Console Logs (If Working)
```
[voice] connectVoice: Getting ephemeral token
[voice] Token acquired, establishing WebSocket connection
[voice] WebSocket OPEN, sending setup config
[voice] WebSocket connection verified OPEN
[voice] enableListening called, isListeningEnabled set to true
[voice] startMicStreaming: requesting microphone access
[voice] Microphone access granted, stream active: true
[voice] Mic streaming started successfully
[voice] Received transcript: your speech here
```

## Error Messages and Solutions

### ❌ "NotAllowedError: Permission denied"
**Cause**: Microphone permission denied by browser/OS
**Fix**: 
- Check browser settings (lock icon in address bar) → allow microphone
- Check Windows Sound Settings → check if microphone is enabled
- Try a different browser
- Restart browser after changing permissions

### ❌ "NotFoundError: No microphone device found"
**Cause**: No microphone connected
**Fix**:
- Connect a microphone to your computer
- Check Windows Sound Settings → Recording → verify microphone is listed and enabled
- If using built-in mic, enable it in device settings

### ❌ "WebSocket CLOSED - code: 1000"
**Cause**: Google API token invalid or connection dropped
**Fix**:
- Check backend is running: `python -m uvicorn app:app --reload` from backend/
- Verify GOOGLE_API_KEY in backend/.env is valid
- Check network connectivity

### ❌ "Token request failed: HTTP 500"
**Cause**: Backend error generating token
**Fix**:
- Check backend is running
- Verify GOOGLE_API_KEY environment variable is set
- Check backend logs for errors
- Try restarting the backend server

### ❌ "WebSocket not OPEN when starting mic streaming"
**Cause**: WebSocket connection didn't establish before mic streaming started
**Fix**:
- This is a timing issue - the fix has been added to the code
- Make sure you're using the latest version
- Try again after page refresh

## Step-by-Step Debugging Process

### Step 1: Verify Backend is Running
```bash
# In backend/ directory
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
Expected output: `Uvicorn running on http://0.0.0.0:8000`

### Step 2: Check Environment Variables
Backend .env should have:
```
GOOGLE_API_KEY=<your_key_here>
```

Frontend .env should have:
```
VITE_BACKEND_URL=http://localhost:8000
```

### Step 3: Test in Browser Console
Open DevTools (F12) → Console and run:
```javascript
// Test 1: Check backend connectivity
fetch('http://localhost:8000/live-token', { method: 'POST' })
  .then(r => r.json())
  .then(d => console.log('Token received:', d))
  .catch(e => console.error('Backend error:', e))
```

### Step 4: Check Microphone in OS Settings
**Windows**:
1. Settings → Privacy & Security → Microphone
2. Make sure "Microphone access" is ON
3. Scroll down and ensure your browser is in the "Allow" list

**macOS**:
1. System Preferences → Security & Privacy → Microphone
2. Ensure browser is in the list

### Step 5: Test Microphone Directly
**Windows**:
1. Settings → Sound → Recording devices
2. Right-click microphone → Properties
3. Go to "Listen" tab → check you can hear yourself
4. Go to "Levels" tab → check input level isn't at 0

## Advanced Debugging

### Check Network Traffic
1. Open DevTools → Network tab
2. Click "Enable voice"
3. Look for a WebSocket connection to `generativelanguage.googleapis.com`
4. If missing: Check browser console for connection errors

### Enable Verbose Logging in Backend
Add to backend/app.py after imports:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Microphone with Different App
1. Use Windows Voice Recorder or similar
2. If microphone doesn't work there either, it's a hardware/OS issue
3. If it works there but not in Swakriti, it's a browser/app issue

## Still Not Working?

1. Check all console logs match expected sequence
2. Share the exact error message from console
3. Verify:
   - Backend is running
   - GOOGLE_API_KEY is valid
   - Microphone works in other apps
   - Browser has microphone permission
   - Browser is up to date

## For Device Name Issue ("swakriti-demo")
If the issue is that a specific device isn't being detected:
1. Check Windows Sound Settings → Recording devices
2. Ensure the device is enabled and set as default
3. The app should auto-detect the default recording device
4. No special device selection is needed in current implementation

---

**Last Updated**: 2026-08-14
**Frontend Voice Implementation**: Google Generative AI Live API
**Backend Token Provider**: Python (genai library)
