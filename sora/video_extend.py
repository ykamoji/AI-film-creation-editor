"""
Video Extension Workflow
========================
Extend an existing Sora-generated video using OpenAI's Videos Extensions API.

Each extension can add up to 20 seconds. A single video can be extended
up to 6 times for a maximum total length of 120 seconds.

Environment variable:  OPENAI_API_KEY

Configuration variables are defined at the top of this file.
"""

import os
import sys
import time
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────

VIDEO_ID = "video_REPLACE_WITH_YOUR_VIDEO_ID"

PROMPT = "Continue the scene as the camera rises over the rooftops and reveals the sunrise."

SECONDS = 10            # Max per extension: 20

OUTPUT_PATH = "extended_video.mp4"

POLL_INTERVAL = 10      # seconds between status checks


# ── Helpers ────────────────────────────────────────────────────────────────

def _validate():
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("ERROR: OPENAI_API_KEY environment variable is not set.")
    if not VIDEO_ID or VIDEO_ID == "video_REPLACE_WITH_YOUR_VIDEO_ID":
        sys.exit("ERROR: Please set VIDEO_ID to a valid video ID.")
    if SECONDS > 20:
        sys.exit("ERROR: Maximum extension duration is 20 seconds.")


def _bar(progress, status, length=30):
    filled = int((progress / 100) * length)
    b = "█" * filled + "░" * (length - filled)
    label = "Queued" if status == "queued" else "Extending"
    sys.stdout.write(f"\r  {label}: [{b}] {progress:.1f}%")
    sys.stdout.flush()


def _poll(client, vid_id):
    while True:
        v = client.videos.retrieve(vid_id)
        p = getattr(v, "progress", 0) or 0
        if v.status in ("completed", "failed"):
            _bar(p, v.status); sys.stdout.write("\n"); return v
        _bar(p, v.status); time.sleep(POLL_INTERVAL)


# ── Main ───────────────────────────────────────────────────────────────────

def extend_video():
    _validate()
    client = OpenAI()

    print(f"\n🔍 Checking source video: {VIDEO_ID}")
    try:
        src = client.videos.retrieve(VIDEO_ID)
    except Exception as e:
        sys.exit(f"❌ Could not retrieve video: {e}")
    if src.status != "completed":
        sys.exit(f"❌ Source status is '{src.status}' — must be 'completed'.")
    print(f"   ✓ Ready (model: {src.model}, duration: {getattr(src, 'seconds', '?')}s)")

    print(f"\n🔗 Submitting extension (+{SECONDS}s)…")
    print(f"   Prompt: {PROMPT[:80]}{'…' if len(PROMPT) > 80 else ''}")

    ext = client.videos.extensions.create(
        video={"id": VIDEO_ID},
        prompt=PROMPT,
        seconds=str(SECONDS),
    )
    ext_id = ext.id
    print(f"\n✅ Extension job → {ext_id}  (status: {ext.status})\n")

    print("⏳ Waiting for completion…")
    ext = _poll(client, ext_id)

    if ext.status == "failed":
        msg = getattr(getattr(ext, "error", None), "message", "Unknown error")
        sys.exit(f"❌ Extension failed: {msg}")

    print(f"\n📥 Downloading to {OUTPUT_PATH}…")
    client.videos.download_content(ext_id, variant="video").write_to_file(OUTPUT_PATH)
    print(f"✅ Saved: {os.path.abspath(OUTPUT_PATH)}")

    print(f"\n{'─'*50}")
    print(f"  Source  : {VIDEO_ID}")
    print(f"  Extended: {ext_id}")
    print(f"  Added   : +{SECONDS}s")
    print(f"  Output  : {os.path.abspath(OUTPUT_PATH)}")
    print(f"{'─'*50}")
    return ext_id


if __name__ == "__main__":
    extend_video()
