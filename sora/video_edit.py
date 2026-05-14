"""
Video Editing Workflow
======================
Edit an existing Sora-generated video using OpenAI's Videos Edits API.

Takes an existing video (by video_id) and applies targeted modifications
described in a prompt — such as changing color palette, lighting, weather,
or camera style — without regenerating the entire clip from scratch.

Environment variable:
    OPENAI_API_KEY  –  Your OpenAI API key.

Configuration variables are defined at the top of this file.
"""

import os
import sys
import time
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

# The video ID of an existing completed Sora generation to edit.
VIDEO_ID = "video_REPLACE_WITH_YOUR_VIDEO_ID"

# Editing prompt — describe the single, well-defined change you want.
# Best results come from focused, specific adjustments:
#   • "Shift the color palette to warm sunset tones with golden backlighting."
#   • "Add gentle snowfall to the scene."
#   • "Change the time of day to night with neon reflections on wet streets."
PROMPT = "Shift the color palette to teal, sand, and rust, with a warm backlight."

# Where to save the edited video
OUTPUT_PATH = "edited_video.mp4"

# Polling interval in seconds
POLL_INTERVAL = 10


# ── Helpers ──────────────────────────────────────────────────────────────────

def _validate_config():
    """Validate configuration before starting."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)

    if not VIDEO_ID or VIDEO_ID == "video_REPLACE_WITH_YOUR_VIDEO_ID":
        print("ERROR: Please set VIDEO_ID to a valid video ID.")
        sys.exit(1)


def _progress_bar(progress: float, status: str, bar_length: int = 30):
    """Print an ASCII progress bar."""
    filled = int((progress / 100) * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    label = "Queued" if status == "queued" else "Editing"
    sys.stdout.write(f"\r  {label}: [{bar}] {progress:.1f}%")
    sys.stdout.flush()


def _poll_until_done(client: OpenAI, video_id: str):
    """Poll the video status until it completes or fails."""
    while True:
        video = client.videos.retrieve(video_id)
        progress = getattr(video, "progress", 0) or 0

        if video.status in ("completed", "failed"):
            _progress_bar(progress, video.status)
            sys.stdout.write("\n")
            return video

        _progress_bar(progress, video.status)
        time.sleep(POLL_INTERVAL)


# ── Main Workflow ────────────────────────────────────────────────────────────

def edit_video():
    """Run the video editing workflow."""
    _validate_config()

    client = OpenAI()

    # ── Verify the source video exists and is completed ──
    print(f"\n🔍 Checking source video: {VIDEO_ID}")
    try:
        source = client.videos.retrieve(VIDEO_ID)
    except Exception as e:
        print(f"❌ Could not retrieve video {VIDEO_ID}: {e}")
        sys.exit(1)

    if source.status != "completed":
        print(f"❌ Source video status is '{source.status}' — must be 'completed' to edit.")
        sys.exit(1)

    print(f"   ✓ Source video is ready (model: {source.model})")

    # ── Submit the edit request ──
    print(f"\n✂️  Submitting edit request…")
    print(f"   Video ID: {VIDEO_ID}")
    print(f"   Prompt:   {PROMPT[:80]}{'…' if len(PROMPT) > 80 else ''}")

    edited_video = client.videos.edits.create(
        video={"id": VIDEO_ID},
        prompt=PROMPT,
    )

    edited_id = edited_video.id
    print(f"\n✅ Edit job created → video_id: {edited_id}")
    print(f"   Status: {edited_video.status}\n")

    # ── Poll for completion ──
    print("⏳ Waiting for edit to complete…")
    edited_video = _poll_until_done(client, edited_id)

    if edited_video.status == "failed":
        error_msg = getattr(getattr(edited_video, "error", None), "message", "Unknown error")
        print(f"\n❌ Video editing failed: {error_msg}")
        sys.exit(1)

    # ── Download the edited video ──
    print(f"\n📥 Downloading edited video to {OUTPUT_PATH}…")
    content = client.videos.download_content(edited_id, variant="video")
    content.write_to_file(OUTPUT_PATH)
    print(f"✅ Edited video saved to: {os.path.abspath(OUTPUT_PATH)}")

    # ── Summary ──
    print(f"\n{'─' * 50}")
    print(f"  Source ID : {VIDEO_ID}")
    print(f"  Edited ID : {edited_id}")
    print(f"  Prompt    : {PROMPT[:60]}{'…' if len(PROMPT) > 60 else ''}")
    print(f"  Output    : {os.path.abspath(OUTPUT_PATH)}")
    print(f"{'─' * 50}")

    return edited_id


if __name__ == "__main__":
    edit_video()
