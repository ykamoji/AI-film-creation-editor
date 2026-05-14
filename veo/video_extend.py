"""
Veo 3.1 — Video Extension Workflow
====================================
Extend a previously generated Veo video by 7 seconds (up to 20 times).

The extension continues the scene from a prior generation, preserving
motion, style, and audio continuity.

Limitations:
  • Only Veo-generated videos can be extended (not uploaded videos).
  • Input videos must be ≤141 seconds, 720p, 16:9 or 9:16.
  • Output includes the original + extension (up to 148s total).
  • Videos are stored for 2 days; referencing resets the timer.
  • Extensions are limited to 720p resolution.

Usage:
  1. First run video_generate.py to create a video.
  2. Copy the operation name printed at the end.
  3. Paste it into PREVIOUS_OPERATION_NAME below and run this script.

  Alternatively, set PREVIOUS_VIDEO_FILE to re-use a saved video object.

Environment variable:
    GEMINI_API_KEY  –  Your Google Gemini API key.
"""

import os
import sys
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

# The operation name from a previous Veo generation.
# Format: "operations/xxxxxx"
# You can get this from the generate script output.
PREVIOUS_OPERATION_NAME = ""

# Alternatively, if you have the previous operation's response cached,
# set this to the video object directly (advanced usage).
# Usually you'll use PREVIOUS_OPERATION_NAME instead.

# Prompt describing how the scene should continue.
PROMPT = "Continue the scene as the camera rises over the rooftops and reveals the sunrise."

# Model variant (must match the model used for the original video)
MODEL = "veo-3.1-generate-preview"

# Resolution — extensions are limited to 720p
RESOLUTION = "720p"

# Number of extension videos to generate (1 or 2)
NUMBER_OF_VIDEOS = 1

# Where to save the extended video
OUTPUT_PATH = "extended_video.mp4"

# Polling interval in seconds
POLL_INTERVAL = 10


# ── Helpers ──────────────────────────────────────────────────────────────────

def _validate_config():
    """Validate configuration before starting."""
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    if not PREVIOUS_OPERATION_NAME:
        print("ERROR: Please set PREVIOUS_OPERATION_NAME to the operation name from a prior generation.")
        print("       Run video_generate.py first and copy the operation name.")
        sys.exit(1)


def _poll_until_done(client, operation):
    """Poll the operation status until the video is ready."""
    while not operation.done:
        sys.stdout.write(f"\r  ⏳ Waiting for video extension to complete...")
        sys.stdout.flush()
        time.sleep(POLL_INTERVAL)
        operation = client.operations.get(operation)

    sys.stdout.write("\r  ✅ Video extension complete!                \n")
    return operation


# ── Main Workflow ────────────────────────────────────────────────────────────

def extend_video():
    """Run the Veo video extension workflow."""
    _validate_config()

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    # ── Retrieve the original video from the previous operation ──
    print(f"\n🔍 Retrieving previous generation: {PREVIOUS_OPERATION_NAME}")

    try:
        prev_operation = types.GenerateVideosOperation(name=PREVIOUS_OPERATION_NAME)
        prev_operation = client.operations.get(prev_operation)
    except Exception as e:
        print(f"❌ Could not retrieve operation: {e}")
        sys.exit(1)

    if not prev_operation.done:
        print("❌ Previous operation is not yet complete. Wait for it to finish first.")
        sys.exit(1)

    if not prev_operation.response or not prev_operation.response.generated_videos:
        print("❌ No generated videos found in the previous operation.")
        sys.exit(1)

    source_video = prev_operation.response.generated_videos[0].video
    print(f"   ✓ Source video retrieved successfully")

    # ── Submit the extension request ──
    print(f"\n🔗 Submitting extension request…")
    print(f"   Model:      {MODEL}")
    print(f"   Resolution: {RESOLUTION}")
    print(f"   Prompt:     {PROMPT[:80]}{'…' if len(PROMPT) > 80 else ''}")

    config = types.GenerateVideosConfig(
        number_of_videos=NUMBER_OF_VIDEOS,
        resolution=RESOLUTION,
    )

    operation = client.models.generate_videos(
        model=MODEL,
        prompt=PROMPT,
        video=source_video,
        config=config,
    )

    print(f"\n✅ Extension job created → operation: {operation.name}")

    # ── Poll for completion ──
    operation = _poll_until_done(client, operation)

    # ── Download the extended video(s) ──
    for vid_idx, gen_video in enumerate(operation.response.generated_videos):
        final_output = OUTPUT_PATH
        if NUMBER_OF_VIDEOS > 1:
            base, ext = os.path.splitext(OUTPUT_PATH)
            final_output = f"{base}_{vid_idx + 1}{ext}"

        print(f"   📥 Downloading to {final_output}…")
        client.files.download(file=gen_video.video)
        gen_video.video.save(final_output)
        print(f"   ✅ Saved: {os.path.abspath(final_output)}")

    # ── Summary ──
    print(f"\n{'═' * 50}")
    print(f"🏁 Extension Complete")
    print(f"   Source operation: {PREVIOUS_OPERATION_NAME}")
    print(f"   New operation:    {operation.name}")
    print(f"   Output:           {os.path.abspath(OUTPUT_PATH)}")
    print(f"{'═' * 50}\n")

    # Return the new operation name so it can be chained for further extensions
    return operation.name


if __name__ == "__main__":
    extend_video()
