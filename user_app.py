"""
USER EXE - Complete Real-time Exercise Reminder
- Listens to Firebase admin_control in real-time
- Auto-starts when admin starts
- Uses admin's interval timing
- Modern dark UI popup with 30-sec auto-close
- Cannot be dismissed by user
- Shows video or placeholder
- Tray icon support
- FULL SCREEN with proper alignment
"""

import os
import sys
import time
import json
import threading
import hashlib
import tempfile
import urllib.request
import pyrebase
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from ffpyplayer.player import MediaPlayer
import winsound

try:
    import pystray
    from PIL import Image as TrayImage
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

# ============================================================
# FIREBASE CONFIGURATION
# ============================================================
firebaseConfig = {
    "apiKey": "YOUR_API_KEY_HERE",
    "authDomain": "exercise-reminder-57378.firebaseapp.com",
    "databaseURL": "https://exercise-reminder-57378-default-rtdb.asia-southeast1.firebasedatabase.app",
    "storageBucket": "exercise-reminder-57378.firebasestorage.app"
}

try:
    firebase = pyrebase.initialize_app(firebaseConfig)
    db = firebase.database()
    FIREBASE_OK = True
except Exception as e:
    print(f"Firebase init error: {e}")
    FIREBASE_OK = False

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def resource_path(relative_path):
    """Get resource path for bundled files"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def download_video_from_url(video_url):
    """Download video from URL and cache locally"""
    try:
        temp_dir = os.path.join(tempfile.gettempdir(), "exercise_videos")
        os.makedirs(temp_dir, exist_ok=True)

        url_hash = hashlib.md5(video_url.encode()).hexdigest()

        file_ext = ".mp4"
        if "." in video_url.split("/")[-1]:
            try:
                file_ext = "." + video_url.split("/")[-1].split("?")[0].split(".")[-1]
            except Exception:
                file_ext = ".mp4"

        local_path = os.path.join(temp_dir, f"{url_hash}{file_ext}")

        # Use cached if exists
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            print(f"✓ Video cached: {local_path}")
            return local_path

        # Download
        print(f"⬇ Downloading video from: {video_url[:60]}...")
        req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
        
        with urllib.request.urlopen(req, timeout=60) as response:
            with open(local_path, "wb") as out_file:
                out_file.write(response.read())

        print(f"✓ Video downloaded: {local_path}")
        return local_path
        
    except Exception as e:
        print(f"❌ Video download failed: {e}")
        return None

def extract_video(resource_video_path):
    """Get playable video path from URL or local file"""
    if not resource_video_path or str(resource_video_path).strip() == "":
        return None

    resource_video_path = str(resource_video_path).strip()

    # Handle external URLs
    if "raw.githubusercontent.com" in resource_video_path or \
       resource_video_path.startswith("http://") or \
       resource_video_path.startswith("https://"):
        return download_video_from_url(resource_video_path)

    # Handle local absolute path
    if os.path.isabs(resource_video_path):
        if os.path.exists(resource_video_path):
            return resource_video_path

    # Handle relative path
    normalized_path = os.path.normpath(resource_video_path)
    if os.path.exists(normalized_path):
        return os.path.abspath(normalized_path)

    # Check relative to script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(script_dir, normalized_path)
    if os.path.exists(local_path):
        return local_path

    # Check videos subfolder
    videos_path = os.path.join(script_dir, "videos", os.path.basename(normalized_path))
    if os.path.exists(videos_path):
        return videos_path

    print(f"⚠ Video not found: {resource_video_path}")
    return None

# ============================================================
# VIDEO PLAYER WIDGET
# ============================================================
class VideoPlayer(tk.Frame):
    """Video player using ffpyplayer with proper sizing"""
    
    def __init__(self, parent, video_path, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.video_path = video_path
        self.player = None
        self.is_playing = True
        self.label = tk.Label(self, bg="#d7dfe8")
        self.label.pack(fill="both", expand=True)

        if not os.path.exists(video_path):
            self.show_error(f"Video file not found:\n{video_path}")
            return

        try:
            print(f"▶ Creating video player: {video_path}")
            self.player = MediaPlayer(video_path, ff_opts={"paused": False, "loop": 0})
            self.after(50, self.update_frame)
        except Exception as e:
            print(f"❌ MediaPlayer error: {e}")
            self.show_error(f"Could not play video:\n{str(e)}")

    def show_error(self, message):
        """Show error message in video area"""
        self.label.config(
            text=message,
            bg="#d7dfe8",
            fg="#a42b2b",
            font=("Segoe UI", 12),
            justify="center"
        )

    def update_frame(self):
        """Update video frame"""
        if not self.player or not self.is_playing:
            return

        try:
            frame, val = self.player.get_frame()

            if val == "eof":
                self.player.seek(0)
                self.after(100, self.update_frame)
                return

            if val == "paused":
                self.after(50, self.update_frame)
                return

            if frame is not None:
                img, _ = frame
                w, h = img.get_size()
                buf = img.to_bytearray()[0]
                pil_image = Image.frombytes("RGB", (w, h), bytes(buf), "raw", "RGB")

                # Get frame container size and fit video to it
                try:
                    frame_width = self.winfo_width()
                    frame_height = self.winfo_height()
                except:
                    frame_width = 680
                    frame_height = 380

                if frame_width > 1 and frame_height > 1:
                    ratio = min(frame_width / w, frame_height / h)
                    new_w = int(w * ratio)
                    new_h = int(h * ratio)
                    pil_image = pil_image.resize((new_w, new_h), Image.LANCZOS)

                photo = ImageTk.PhotoImage(pil_image)
                self.label.config(image=photo)
                self.label.image = photo

            self.after(33, self.update_frame)

        except Exception as e:
            print(f"Frame update error: {e}")
            self.after(100, self.update_frame)

    def stop(self):
        """Stop video playback"""
        self.is_playing = False
        if self.player:
            try:
                self.player.close_player()
            except Exception:
                pass

# ============================================================
# MAIN USER APP
# ============================================================
class UserReminderApp:
    """User-side exercise reminder app with real-time Firebase sync"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Exercise Reminder - User")
        self.root.geometry("500x400")
        self.root.withdraw()  # Hide initially

        # State
        self.admin_state = {
            "is_running": False,
            "interval_minutes": 60,
            "last_updated": 0
        }

        self.current_interval = 60
        self.is_running = False
        self.exercises = []
        self.exercise_index = 0

        self.reminder_thread = None
        self.next_trigger = time.time() + self.current_interval * 60
        self.current_popup = None
        self.popup_timer = None

        # Load logo
        self.logo_img = None
        logo_path = resource_path("logo.png")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                img = img.resize((120, 50))
                self.logo_img = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Logo load error: {e}")

        # Initialize
        print("="*60)
        print("USER REMINDER APP STARTING")
        print("="*60)

        if FIREBASE_OK:
            self.load_exercises()
            self.check_initial_admin_state()
            self.start_admin_listener()
            self.start_exercises_listener()
        else:
            messagebox.showerror("Firebase Error", "Firebase connection failed")
            return

        self.show_tray_icon()
        self.root.after(1000, self.periodic_check)

    def periodic_check(self):
        """Keep app alive"""
        self.root.after(1000, self.periodic_check)

    def show_tray_icon(self):
        """Show system tray icon"""
        if not HAS_TRAY:
            print("⚠ Tray icon not available (pystray not installed)")
            return

        try:
            icon_path = resource_path("logo.png")
            if os.path.exists(icon_path):
                icon_img = TrayImage.open(icon_path)
            else:
                icon_img = TrayImage.new("RGB", (64, 64), color="#1d2f46")

            def on_quit(icon, item):
                self.exit_application()

            def on_open(icon, item):
                if self.current_popup and self.current_popup.winfo_exists():
                    self.current_popup.lift()

            self.tray_icon = pystray.Icon(
                "Exercise Reminder",
                icon_img,
                "Exercise Reminder",
                menu=pystray.Menu(
                    pystray.MenuItem("Open", on_open),
                    pystray.MenuItem("Quit", on_quit)
                )
            )
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            print("✓ Tray icon created")
        except Exception as e:
            print(f"⚠ Tray icon error: {e}")

    def exit_application(self):
        """Exit app cleanly"""
        print("🛑 Exiting application...")
        self.is_running = False
        
        if self.current_popup and self.current_popup.winfo_exists():
            try:
                self.current_popup.destroy()
            except Exception:
                pass

        try:
            if hasattr(self, "tray_icon"):
                self.tray_icon.stop()
        except Exception:
            pass

        self.root.destroy()
        sys.exit(0)

    # ========== FIREBASE LISTENERS ==========

    def start_admin_listener(self):
        """Real-time listener for admin_control"""
        print("📡 Starting admin_control listener...")

        def stream_handler(message):
            try:
                if not isinstance(message, dict):
                    return

                event = message.get("event")
                data = message.get("data")

                print(f"\n🔔 ADMIN UPDATE RECEIVED")
                print(f"   Event: {event}")
                print(f"   Path: {message.get('path')}")
                print(f"   Data: {data}")

                if event in ["put", "patch"] and isinstance(data, dict):
                    old_running = self.admin_state["is_running"]
                    old_interval = self.admin_state["interval_minutes"]

                    # Update state
                    self.admin_state["is_running"] = bool(data.get("is_running", False))
                    
                    interval = data.get("interval_minutes", self.current_interval)
                    try:
                        interval = int(interval)
                    except Exception:
                        interval = self.current_interval

                    if interval > 0:
                        self.current_interval = interval

                    self.admin_state["interval_minutes"] = self.current_interval
                    self.admin_state["last_updated"] = int(time.time())

                    print(f"   New State: running={self.admin_state['is_running']}, interval={self.current_interval}min")

                    # React to changes
                    if self.admin_state["is_running"] and not old_running:
                        print("   👉 ADMIN STARTED - Starting reminders on this device")
                        self.root.after(0, self.start_reminders)
                    elif not self.admin_state["is_running"] and old_running:
                        print("   👉 ADMIN STOPPED - Stopping reminders on this device")
                        self.root.after(0, self.stop_reminders)
                    elif self.current_interval != old_interval and self.is_running:
                        print(f"   👉 INTERVAL CHANGED - Resetting timer")
                        self.next_trigger = time.time() + (self.current_interval * 60)

            except Exception as e:
                print(f"❌ Stream handler error: {e}")

        def run_stream():
            while True:
                try:
                    print("🚀 Streaming admin_control...")
                    db.child("admin_control").stream(stream_handler)
                    break
                except Exception as e:
                    print(f"❌ Admin listener failed, retrying in 5s: {e}")
                    time.sleep(5)

        threading.Thread(target=run_stream, daemon=True).start()

    def start_exercises_listener(self):
        """Real-time listener for exercises"""
        print("📡 Starting exercises listener...")

        def stream_handler(message):
            try:
                if not isinstance(message, dict):
                    return

                event = message.get("event")

                if event in ["put", "patch"]:
                    self.load_exercises()
                    print(f"✓ Exercises synced: {len(self.exercises)} total")
            except Exception as e:
                print(f"Exercise stream error: {e}")

        def run_stream():
            while True:
                try:
                    db.child("exercises").stream(stream_handler)
                    break
                except Exception as e:
                    print(f"❌ Exercise listener failed, retrying in 5s: {e}")
                    time.sleep(5)

        threading.Thread(target=run_stream, daemon=True).start()

    def check_initial_admin_state(self):
        """Load initial admin state"""
        print("📊 Checking initial admin state...")
        try:
            state = db.child("admin_control").get().val()
            if isinstance(state, dict):
                self.admin_state = {
                    "is_running": bool(state.get("is_running", False)),
                    "interval_minutes": int(state.get("interval_minutes", 60)),
                    "last_updated": int(state.get("last_updated", 0))
                }
                self.current_interval = self.admin_state["interval_minutes"]
                
                if self.admin_state["is_running"]:
                    print(f"✓ Admin is running - interval: {self.current_interval}min")
                    self.start_reminders()
                else:
                    print("✓ Admin is stopped - waiting for signal")
            else:
                print("⚠ No admin state found - using defaults")
        except Exception as e:
            print(f"⚠ Initial state check error: {e}")

    def load_exercises(self):
        """Load exercises from Firebase"""
        try:
            data = db.child("exercises").get().val()
            self.exercises = []

            if isinstance(data, dict):
                for key, ex in data.items():
                    if isinstance(ex, dict):
                        ex["_key"] = key
                        self.exercises.append(ex)

            print(f"✓ Loaded {len(self.exercises)} exercises")
        except Exception as e:
            print(f"❌ Exercise load error: {e}")

    # ========== REMINDER LOGIC ==========

    def pick_exercise(self):
        """Get next exercise (round-robin)"""
        if not self.exercises:
            return None

        self.exercise_index = int(time.time() // 60) % len(self.exercises)
        return self.exercises[self.exercise_index]

    def start_reminders(self):
        """Start the reminder loop"""
        if self.is_running or not self.exercises:
            return

        self.is_running = True
        self.next_trigger = time.time() + (self.current_interval * 60)
        
        print(f"\n✅ REMINDERS STARTED")
        print(f"   Interval: {self.current_interval} minutes")
        print(f"   Exercises: {len(self.exercises)}")

        self.reminder_thread = threading.Thread(target=self.reminder_loop, daemon=True)
        self.reminder_thread.start()

    def stop_reminders(self):
        """Stop the reminder loop"""
        self.is_running = False
        
        if self.current_popup and self.current_popup.winfo_exists():
            try:
                self.current_popup.destroy()
            except Exception:
                pass
        self.current_popup = None

        print(f"\n⏹️ REMINDERS STOPPED")

    def reminder_loop(self):
        """Main reminder loop"""
        while self.is_running and self.admin_state["is_running"]:
            now = time.time()

            if now >= self.next_trigger:
                exercise = self.pick_exercise()
                if exercise:
                    print(f"\n🔔 SHOWING: {exercise.get('name')}")
                    self.root.after(0, lambda ex=exercise: self.show_popup(ex))
                
                self.next_trigger = time.time() + (self.current_interval * 60)

            time.sleep(0.5)

    # ========== MODERN POPUP UI - FULL SCREEN ==========

    def show_popup(self, exercise):
        """Show modern full-screen exercise reminder popup"""
        
        # Close previous popup
        if self.current_popup and self.current_popup.winfo_exists():
            try:
                self.current_popup.destroy()
            except Exception:
                pass

        # Create custom full-screen window
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)  # Remove window frame
        popup.attributes("-topmost", True)
        popup.configure(bg="#071a25")

        self.current_popup = popup

        # Make full screen
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        popup.geometry(f"{screen_w}x{screen_h}+0+0")

        # Background canvas
        bg = tk.Canvas(
            popup,
            width=screen_w,
            height=screen_h,
            bg="#071a25",
            highlightthickness=0
        )
        bg.pack(fill="both", expand=True)

        # Center card dimensions
        card_w = min(1200, screen_w - 100)
        card_h = min(850, screen_h - 100)
        card_x = (screen_w - card_w) // 2
        card_y = (screen_h - card_h) // 2

        # Card background with border
        bg.create_rectangle(
            card_x, card_y,
            card_x + card_w, card_y + card_h,
            fill="#0d1f2d",
            outline="#2a4051",
            width=3
        )

        # Top-right timer
        timer_var = tk.StringVar(value="0:30")
        timer_label = tk.Label(
            popup,
            textvariable=timer_var,
            bg="#071a25",
            fg="#edf3f8",
            font=("Segoe UI", 16, "bold")
        )
        timer_label.place(x=screen_w - 150, y=40)

        # Main content frame
        content_frame = tk.Frame(
            popup,
            bg="#0d1f2d",
            width=card_w,
            height=card_h
        )
        content_frame.place(x=card_x, y=card_y, width=card_w, height=card_h)

        # Title
        title = tk.Label(
            content_frame,
            text="Exercise Reminder",
            bg="#0d1f2d",
            fg="#edf3f8",
            font=("Segoe UI", 40, "bold")
        )
        title.pack(pady=(40, 10))

        # Logo instead of circles
        if self.logo_img:
            logo_label = tk.Label(
                content_frame,
                image=self.logo_img,
                bg="#0d1f2d"
            )
            logo_label.pack(pady=(0, 20))
        else:
            # Fallback if logo not available
            icon = tk.Label(
                content_frame,
                text="◌◌",
                bg="#0d1f2d",
                fg="#d8e2eb",
                font=("Segoe UI", 40)
            )
            icon.pack(pady=(0, 20))

        # Subtitle
        subtitle = tk.Label(
            content_frame,
            text="Take a breather, stretch your body, refocus your mind.",
            bg="#0d1f2d",
            fg="#cfe0ef",
            font=("Segoe UI", 18)
        )
        subtitle.pack(pady=(0, 30))

        # Video container with proper sizing
        video_w = card_w - 120
        video_h = 400

        # Glowing border effect
        bg.create_rectangle(
            card_x + 60, card_y + 280,
            card_x + 60 + video_w, card_y + 280 + video_h,
            outline="#9bb8ff",
            width=4
        )

        # Video frame
        video_container = tk.Frame(
            content_frame,
            bg="#d7dfe8",
            highlightthickness=0
        )
        video_container.pack(fill="both", expand=True, padx=60, pady=(0, 30))

        # Exercise description (instead of "Exercise Video")
        exercise_name = exercise.get("name", "Exercise")
        exercise_desc = exercise.get("desc", "")
        
        if exercise_desc:
            # Show description as header
            desc_label = tk.Label(
                video_container,
                text=exercise_desc,
                bg="#d7dfe8",
                fg="#1a1c20",
                font=("Segoe UI", 14, "italic"),
                wraplength=video_w - 40
            )
            desc_label.pack(anchor="w", padx=20, pady=(15, 10))
        else:
            # Show exercise name if no description
            name_label = tk.Label(
                video_container,
                text=exercise_name,
                bg="#d7dfe8",
                fg="#1a1c20",
                font=("Segoe UI", 18, "bold")
            )
            name_label.pack(anchor="w", padx=20, pady=(15, 10))

        # Video content
        video_url = exercise.get("video", "").strip()
        if video_url:
            try:
                playable_video = extract_video(video_url)
                if playable_video and os.path.exists(playable_video):
                    player = VideoPlayer(video_container, playable_video)
                    player.pack(fill="both", expand=True, padx=0, pady=(0, 0))
                    print(f"✓ Video playing: {os.path.basename(playable_video)}")
                else:
                    error_label = tk.Label(
                        video_container,
                        text="📺 Video unavailable",
                        bg="#d7dfe8",
                        fg="#5d6473",
                        font=("Segoe UI", 20)
                    )
                    error_label.pack(expand=True)
            except Exception as e:
                print(f"❌ Video load error: {e}")
                error_label = tk.Label(
                    video_container,
                    text=f"Error: {str(e)[:50]}",
                    bg="#d7dfe8",
                    fg="#a42b2b",
                    font=("Segoe UI", 14)
                )
                error_label.pack(expand=True)
        else:
            placeholder = tk.Label(
                video_container,
                text="ℹ️ No video for this exercise",
                bg="#d7dfe8",
                fg="#5d6473",
                font=("Segoe UI", 20)
            )
            placeholder.pack(expand=True)

        # Play sound alert
        try:
            winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception:
            pass

        # Auto-close timer
        remaining = 30
        self.popup_timer = {"remaining": remaining, "var": timer_var}

        def countdown():
            if not self.current_popup or not self.current_popup.winfo_exists():
                return

            if self.popup_timer is None:
                return

            remaining = self.popup_timer["remaining"]
            remaining -= 1

            if remaining <= 0:
                try:
                    if self.current_popup and self.current_popup.winfo_exists():
                        self.current_popup.destroy()
                    self.current_popup = None
                    self.popup_timer = None
                    print("✓ Popup auto-closed")
                    return
                except Exception:
                    pass

            self.popup_timer["remaining"] = remaining
            mins = remaining // 60
            secs = remaining % 60
            self.popup_timer["var"].set(f"{mins}:{secs:02d}")
            
            if self.current_popup and self.current_popup.winfo_exists():
                self.current_popup.after(1000, countdown)

        self.current_popup.after(1000, countdown)

# ============================================================
# START APP
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Exercise Reminder")
    root.geometry("400x300")
    root.withdraw()

    app = UserReminderApp(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nShutdown...")
        app.exit_application()
