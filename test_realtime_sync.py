"""
TEST SCRIPT - Test real-time sync without building EXE
Run this to simulate admin and user devices communicating

Usage:
1. Open TWO terminal windows
2. Terminal 1: python test_admin.py
3. Terminal 2: python test_user.py
4. Click buttons in Terminal 1 (admin) and watch Terminal 2 (user) respond instantly!
"""

import time
import threading
import pyrebase

# Your Firebase config
firebaseConfig = {
    "apiKey": "AIzaSyD5xxxxxxxxxxx",  # Replace with your config
    "authDomain": "exercise-reminder-57378.firebaseapp.com",
    "databaseURL": "https://exercise-reminder-57378-default-rtdb.asia-southeast1.firebasedatabase.app",
    "storageBucket": "exercise-reminder-57378.firebasestorage.app"
}

firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

print("✓ Firebase initialized")
print(f"✓ Database URL: {firebaseConfig['databaseURL']}\n")
