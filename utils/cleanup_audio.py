# utils/cleanup_audio.py
"""
Deletes audio files in static/audio/ older than a specified age (default: 24 hours).
Recommended to run as a daily cronjob or scheduled task.
"""

import os
import time
from datetime import datetime, timedelta

def cleanup_old_audio_files(directory="static/audio", max_age_hours=24):
    now = time.time()
    cutoff = now - max_age_hours * 3600
    deleted = []
    if not os.path.exists(directory):
        return deleted
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < cutoff:
                os.remove(file_path)
                deleted.append(filename)
    return deleted

if __name__ == "__main__":
    deleted = cleanup_old_audio_files()
    print(f"Deleted {len(deleted)} old audio files: {deleted}")
