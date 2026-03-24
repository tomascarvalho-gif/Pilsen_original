import os
import time
import subprocess

LOG_FILE = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/taxonomy_video_classification.log"
TIMEOUT_MINUTES = 10

def show_notification(title, message):
    applescript = f'display notification "{message}" with title "{title}" sound name "Basso"'
    subprocess.run(["osascript", "-e", applescript])

def monitor_log():
    print(f"Watchdog started. Monitoring {LOG_FILE} for inactivity > {TIMEOUT_MINUTES} minutes...")
    while True:
        try:
            if not os.path.exists(LOG_FILE):
                time.sleep(60)
                continue
                
            last_modified = os.path.getmtime(LOG_FILE)
            current_time = time.time()
            minutes_idle = (current_time - last_modified) / 60
            
            # Check if process is still running
            ps = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            process_running = 'taxonomy_video_test.py' in ps.stdout
            
            if minutes_idle > TIMEOUT_MINUTES:
                msg = f"Video taxonomy script hasn't updated its log in {int(minutes_idle)} minutes. It might be stuck on a corrupted file."
                print(msg)
                show_notification("Synapsee AI Alert!", msg)
                # Don't spam, sleep for 30 mins after an alert
                time.sleep(1800)
            elif not process_running:
                msg = "The taxonomy_video_test.py process has died or finished."
                print(msg)
                show_notification("Synapsee AI Update", msg)
                # Exit once the process stops naturally (or dies)
                break
                
        except Exception as e:
            print(f"Monitor error: {e}")
            
        time.sleep(60) # Check every 60 seconds

if __name__ == "__main__":
    monitor_log()
