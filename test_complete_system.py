"""
COMPLETE SYSTEM TEST
Test admin-to-user real-time sync

Usage:
1. Update firebaseConfig with your credentials
2. Run: python test_complete_system.py
3. Follow the prompts

This will:
- Connect to Firebase
- Test admin control writes
- Test user listener updates
- Show real-time sync working
"""

import time
import threading
import pyrebase

# Your Firebase config - REPLACE WITH YOUR CREDENTIALS
firebaseConfig = {
    "apiKey": "AIzaSyD5xxxxxxxxxxx",
    "authDomain": "exercise-reminder-57378.firebaseapp.com",
    "databaseURL": "https://exercise-reminder-57378-default-rtdb.asia-southeast1.firebasedatabase.app",
    "storageBucket": "exercise-reminder-57378.firebasestorage.app"
}

firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

print("="*80)
print("EXERCISE REMINDER - COMPLETE SYSTEM TEST")
print("="*80)

# Test 1: Check Firebase connection
print("\n[TEST 1] Firebase Connection")
try:
    test = db.child("test").get().val()
    print("✓ Firebase connection successful")
except Exception as e:
    print(f"✗ Firebase connection failed: {e}")
    exit(1)

# Test 2: Write to admin_control
print("\n[TEST 2] Writing to admin_control")
try:
    db.child("admin_control").update({
        "is_running": False,
        "interval_minutes": 60,
        "last_updated": int(time.time())
    })
    print("✓ Write successful")
except Exception as e:
    print(f"✗ Write failed: {e}")
    exit(1)

# Test 3: Real-time listener
print("\n[TEST 3] Real-time Listener (User POV)")
print("Listening to admin_control changes...")

update_received = []

def stream_handler(message):
    print(f"\n🔔 UPDATE RECEIVED:")
    print(f"   Event: {message.get('event')}")
    print(f"   Path: {message.get('path')}")
    print(f"   Data: {message.get('data')}")
    update_received.append(True)

def run_listener():
    try:
        db.child("admin_control").stream(stream_handler)
    except Exception as e:
        print(f"Listener error: {e}")

listener_thread = threading.Thread(target=run_listener, daemon=True)
listener_thread.start()

time.sleep(2)

# Test 4: Admin broadcasts START
print("\n[TEST 4] Admin Broadcasting START Signal")
print("Sending: is_running=True, interval_minutes=5")

db.child("admin_control").update({
    "is_running": True,
    "interval_minutes": 5,
    "last_updated": int(time.time())
})

time.sleep(3)

if update_received:
    print("✓ User received update!")
else:
    print("⚠ No update received yet (might still arrive)")

# Test 5: Admin changes interval
print("\n[TEST 5] Admin Updating Interval")
print("Sending: interval_minutes=2")

db.child("admin_control").update({
    "interval_minutes": 2,
    "last_updated": int(time.time())
})

time.sleep(2)

# Test 6: Admin broadcasts STOP
print("\n[TEST 6] Admin Broadcasting STOP Signal")
print("Sending: is_running=False")

db.child("admin_control").update({
    "is_running": False,
    "last_updated": int(time.time())
})

time.sleep(2)

# Summary
print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

print("""
✓ If you saw 'UPDATE RECEIVED' multiple times above, your system is working!

Next Steps:
1. Open TWO terminal windows
2. Terminal 1: python admin_app.py
3. Terminal 2: python user_app.py
4. Login to admin in Terminal 1
5. Click "START ALL REMINDERS"
6. Watch Terminal 2 respond instantly!

Firebase Rules Check:
Make sure your Firebase Realtime Database rules allow reads/writes:
{
  "rules": {
    "admin_control": {
      ".read": true,
      ".write": "auth != null"
    },
    "exercises": {
      ".read": true,
      ".write": "auth != null"
    }
  }
}

Go to: https://console.firebase.google.com/
Project Settings → Realtime Database → Rules
""")

print("="*80)
