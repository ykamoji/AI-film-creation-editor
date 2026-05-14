"""
Video Generation Workflow
=========================
Generate a new video using OpenAI's Sora 2 API with optional reference images.

Supports up to 14 reference images provided as local file paths. The first
image is sent as `input_reference` (the opening-frame guide). Any additional
images (up to 13 more) are uploaded via the Files API and passed as extra
input references in a follow-up JSON request.

Environment variable:
    OPENAI_API_KEY  –  Your OpenAI API key.

Configuration variables are defined at the top of this file so you can
adjust them without touching the logic.
"""

import os
import sys
import time
import pathlib
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

# Text prompt describing the desired video
PROMPT = """
Cinematography: Shaky handheld medium-shot, extreme motion blur, 180-degree shutter. High-speed kinetic tracking.

Subject: Blindfolded man and a woman fighter. The man’s right shoulder and right arm are completely frozen, locked, and pinned behind his back as a static element.
Action: A hyper-fast 2x speed duel. The man defends with a one-armed combat style, using strictly and exclusively his left arm for every block and parry. The left arm moves with lightning speed while the right arm remains a dead-weight, tucked behind him. The woman strikes with high-velocity kicks.

Mechanical Constraint: Zero movement in the right limb. High displacement and explosive speed in the left limb and legs. Total asymmetry in combat.

Environment: Gritty training room, high-contrast lighting, raw action aesthetic.
"""

# Model: "sora-2" (fast / flexible) or "sora-2-pro" (higher quality)
MODEL = "sora-2"

# Video dimensions – must match reference image dimensions if provided.
# Common sizes: "480x480", "1024x576", "576x1024", "1280x720", "720x1280",
#               "1920x1080", "1080x1920" (1080p requires sora-2-pro)
SIZE = "1280x720"

# Duration in seconds (supported: 4, 8, 12)
SECONDS = 8

# List of reference image file paths (up to 14).
# The first image acts as the opening-frame guide (input_reference).
# Leave the list empty for a pure text-to-video generation.
INPUT_REFERENCE_IMAGES = [
    # "/path/to/reference_image_1.png",
    # "/path/to/reference_image_2.jpg",
    # ... up to 14 images
    "/Users/ykamoji/Documents/Audiobook_media/Vanessa(Chapter 130).png"
]

# Where to save the downloaded MP4 file
OUTPUT_PATH = "generated_video.mp4"

# Polling interval in seconds when waiting for the render job
POLL_INTERVAL = 10


# ── Helpers ──────────────────────────────────────────────────────────────────

def _validate_config():
    """Validate configuration before starting."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)

    if len(INPUT_REFERENCE_IMAGES) > 14:
        print("ERROR: A maximum of 14 reference images is allowed.")
        sys.exit(1)

    for img_path in INPUT_REFERENCE_IMAGES:
        p = pathlib.Path(img_path)
        if not p.exists():
            print(f"ERROR: Reference image not found: {img_path}")
            sys.exit(1)
        ext = p.suffix.lower()
        if ext not in (".jpeg", ".jpg", ".png", ".webp"):
            print(f"ERROR: Unsupported image format '{ext}' for {img_path}. Use JPEG, PNG, or WebP.")
            sys.exit(1)


def _upload_image(client: OpenAI, image_path: str) -> str:
    """Upload an image to OpenAI Files API and return the file_id."""
    print(f"  Uploading reference image: {image_path}")
    with open(image_path, "rb") as f:
        uploaded = client.files.create(file=f, purpose="vision")
    print(f"  ✓ Uploaded → file_id: {uploaded.id}")
    return uploaded.id


def _progress_bar(progress: float, status: str, bar_length: int = 30):
    """Print an ASCII progress bar."""
    filled = int((progress / 100) * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    label = "Queued" if status == "queued" else "Rendering"
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

def generate_video():
    """Run the video generation workflow."""
    _validate_config()

    client = OpenAI()

    # ── Process each reference image ──
    # If no images are provided, we run once with text-to-video.
    images_to_process = INPUT_REFERENCE_IMAGES if INPUT_REFERENCE_IMAGES else [None]
    
    video_ids = []

    for i, img_path in enumerate(images_to_process):
        print(f"\n{'─' * 50}")
        if img_path:
            print(f"📸 Processing Image {i+1}/{len(images_to_process)}: {img_path}")
        else:
            print(f"🎬 Starting Text-to-Video generation…")

        # ── Build request parameters ──
        # We use extra_body to pass input_reference as a JSON object,
        # which satisfies the backend and avoids SDK multipart conflicts.
        create_kwargs = {
            "model": MODEL,
            "prompt": PROMPT,
            "size": SIZE,
            "seconds": str(SECONDS),
        }

        if img_path:
            print(f"   Uploading reference to Files API…")
            with open(img_path, "rb") as f:
                uploaded = client.files.create(file=f, purpose="vision")
            
            # Pass the reference as an object in extra_body
            create_kwargs["extra_body"] = {
                "input_reference": {"file_id": uploaded.id}
            }
            # Explicitly set Content-Type to application/json to override SDK default
            create_kwargs["extra_headers"] = {
                "Content-Type": "application/json"
            }
            print(f"   ✓ Uploaded → {uploaded.id}")

        try:
            # ── Start the render job ──
            print(f"   Model:    {MODEL}")
            print(f"   Size:     {SIZE}")
            print(f"   Duration: {SECONDS}s")
            
            video = client.videos.create(**create_kwargs)
            video_id = video.id
            video_ids.append(video_id)
            print(f"\n✅ Render job created → video_id: {video_id}")
            print(f"   Status: {video.status}\n")

            # ── Poll for completion ──
            print("⏳ Waiting for render to complete…")
            video = _poll_until_done(client, video_id)

            if video.status == "failed":
                error_msg = getattr(getattr(video, "error", None), "message", "Unknown error")
                print(f"\n❌ Video generation failed: {error_msg}")
                continue

            # ── Download the final MP4 ──
            final_output = OUTPUT_PATH
            if len(images_to_process) > 1:
                base, ext = os.path.splitext(OUTPUT_PATH)
                final_output = f"{base}_{i+1}{ext}"

            print(f"\n📥 Downloading video to {final_output}…")
            content = client.videos.download_content(video_id, variant="video")
            content.write_to_file(final_output)
            print(f"✅ Video saved to: {os.path.abspath(final_output)}")

        except Exception as e:
            print(f"\n❌ Error during generation: {e}")
            continue

    # ── Final Summary ──
    print(f"\n{'═' * 50}")
    print(f"🏁 Workflow Complete")
    print(f"   Total Videos: {len(video_ids)}")
    if video_ids:
        print(f"   Video IDs:    {', '.join(video_ids)}")
    print(f"{'═' * 50}\n")

    return video_ids


if __name__ == "__main__":
    generate_video()
