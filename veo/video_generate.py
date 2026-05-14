"""
Veo 3.1 — Video Generation Workflow
====================================
Generate videos using Google's Veo 3.1 model via the Gemini API.

Supports:
  • Pure text-to-video generation
  • Single image as the opening frame (image parameter)
  • Up to 3 reference images per request to guide content (reference_images)
  • Up to 14 reference images total — batched into groups of 3

The script will automatically batch reference images into groups of up to 3
(the API maximum per request) and generate one video per batch.

Environment variable:
    GEMINI_API_KEY  –  Your Google Gemini API key.

Configuration variables are defined at the top of this file.
"""

import os
import sys
import time
import base64
import pathlib
from google import genai
from google.genai import types
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
# Model variant:
#   "veo-3.1-generate-preview"       — Veo 3.1 (highest quality, native audio)
#   "veo-3.1-lite-generate-preview"  — Veo 3.1 Lite (faster, no 4k)
MODEL = "veo-3.1-generate-preview"

# Aspect ratio: "16:9" (landscape) or "9:16" (portrait)
ASPECT_RATIO = "16:9"

# Resolution: "720p", "1080p", or "4k" (4k not available for Lite)
# Higher resolution = higher latency and cost.
# Video extension is limited to 720p.
RESOLUTION = "720p"

# Number of videos to generate per request (1 or 2)
NUMBER_OF_VIDEOS = 1

# List of reference image file paths (up to 14).
# These guide the generated video's content (person, character, product).
# Images are batched into groups of 3 (the API maximum per request).
# Leave empty for a pure text-to-video generation.
# Set reference_type to "subject" for people/characters or "asset" for objects.
INPUT_REFERENCE_IMAGES = [
    # "/path/to/reference_image_1.png",
    # "/path/to/reference_image_2.jpg",
    # ... up to 14 images
    "/Users/ykamoji/Documents/Audiobook_media/Vanessa(Chapter 130).png"
]

# Reference type for all images: "subject" (person/character) or "asset" (object/product)
REFERENCE_TYPE = "asset"

# Optional: path to a single image to use as the video's opening frame.
# This is different from reference images — it sets the first frame directly.
# Leave as None to skip.
FIRST_FRAME_IMAGE = None

# Optional: path to a single image to use as the video's last frame.
# Combined with FIRST_FRAME_IMAGE for interpolation.
# Leave as None to skip.
LAST_FRAME_IMAGE = None

# Where to save the downloaded MP4 file(s)
OUTPUT_PATH = "generated_video.mp4"

# Polling interval in seconds when waiting for the render job
POLL_INTERVAL = 10


# ── Helpers ──────────────────────────────────────────────────────────────────

def _validate_config():
    """Validate configuration before starting."""
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    if len(INPUT_REFERENCE_IMAGES) > 14:
        print("ERROR: A maximum of 14 reference images is allowed.")
        sys.exit(1)

    all_images = list(INPUT_REFERENCE_IMAGES)
    if FIRST_FRAME_IMAGE:
        all_images.append(FIRST_FRAME_IMAGE)
    if LAST_FRAME_IMAGE:
        all_images.append(LAST_FRAME_IMAGE)

    for img_path in all_images:
        p = pathlib.Path(img_path)
        if not p.exists():
            print(f"ERROR: Image not found: {img_path}")
            sys.exit(1)
        ext = p.suffix.lower()
        if ext not in (".jpeg", ".jpg", ".png", ".webp"):
            print(f"ERROR: Unsupported image format '{ext}' for {img_path}. Use JPEG, PNG, or WebP.")
            sys.exit(1)


def _load_image(image_path: str) -> types.Image:
    """Load an image from disk and return a google.genai Image object."""
    p = pathlib.Path(image_path)
    ext = p.suffix.lower()
    mime_map = {".jpeg": "image/jpeg", ".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/png")

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    return types.Image(image_bytes=image_bytes, mime_type=mime_type)


def _batch_images(images: list, batch_size: int = 3) -> list:
    """Split a list of images into batches of batch_size."""
    return [images[i:i + batch_size] for i in range(0, len(images), batch_size)]


def _poll_until_done(client, operation):
    """Poll the operation status until the video is ready."""
    while not operation.done:
        sys.stdout.write(f"\r  ⏳ Waiting for video generation to complete...")
        sys.stdout.flush()
        time.sleep(POLL_INTERVAL)
        operation = client.operations.get(operation)

    sys.stdout.write("\r  ✅ Video generation complete!              \n")
    return operation


# ── Main Workflow ────────────────────────────────────────────────────────────

def generate_video():
    """Run the Veo video generation workflow."""
    _validate_config()

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    # ── Determine generation mode ──
    has_references = len(INPUT_REFERENCE_IMAGES) > 0
    has_first_frame = FIRST_FRAME_IMAGE is not None
    has_last_frame = LAST_FRAME_IMAGE is not None

    video_ids = []

    if has_references:
        # ── Reference Images Mode ──
        # Batch into groups of 3 (API max per request)
        batches = _batch_images(INPUT_REFERENCE_IMAGES, batch_size=3)
        print(f"\n📸 {len(INPUT_REFERENCE_IMAGES)} reference image(s) → {len(batches)} batch(es) of ≤3")

        for batch_idx, batch in enumerate(batches):
            print(f"\n{'─' * 50}")
            print(f"🎬 Batch {batch_idx + 1}/{len(batches)}")

            # Build reference image objects
            ref_images = []
            for img_path in batch:
                print(f"   Loading: {img_path}")
                img = _load_image(img_path)
                ref_images.append(
                    types.VideoGenerationReferenceImage(
                        image=img,
                        reference_type=REFERENCE_TYPE,
                    )
                )

            config = types.GenerateVideosConfig(
                aspect_ratio=ASPECT_RATIO,
                resolution=RESOLUTION,
                number_of_videos=NUMBER_OF_VIDEOS,
                reference_images=ref_images,
            )

            print(f"   Model:      {MODEL}")
            print(f"   Aspect:     {ASPECT_RATIO}")
            print(f"   Resolution: {RESOLUTION}")
            print(f"   References: {len(ref_images)}")

            operation = client.models.generate_videos(
                model=MODEL,
                prompt=PROMPT,
                config=config,
            )

            operation = _poll_until_done(client, operation)

            # Download each generated video
            for vid_idx, gen_video in enumerate(operation.response.generated_videos):
                final_output = OUTPUT_PATH
                if len(batches) > 1 or NUMBER_OF_VIDEOS > 1:
                    base, ext = os.path.splitext(OUTPUT_PATH)
                    final_output = f"{base}_b{batch_idx + 1}_v{vid_idx + 1}{ext}"

                print(f"   📥 Downloading to {final_output}…")
                client.files.download(file=gen_video.video)
                gen_video.video.save(final_output)
                print(f"   ✅ Saved: {os.path.abspath(final_output)}")
                video_ids.append(final_output)

    elif has_first_frame or has_last_frame:
        # ── Frame-Based Mode (first frame / interpolation) ──
        print(f"\n{'─' * 50}")
        print(f"🖼  Frame-based generation")

        first_image = _load_image(FIRST_FRAME_IMAGE) if has_first_frame else None
        last_image = _load_image(LAST_FRAME_IMAGE) if has_last_frame else None

        config_kwargs = {
            "aspect_ratio": ASPECT_RATIO,
            "resolution": RESOLUTION,
            "number_of_videos": NUMBER_OF_VIDEOS,
        }
        if last_image:
            config_kwargs["last_frame"] = last_image

        config = types.GenerateVideosConfig(**config_kwargs)

        print(f"   Model:      {MODEL}")
        print(f"   Aspect:     {ASPECT_RATIO}")
        print(f"   Resolution: {RESOLUTION}")
        if has_first_frame:
            print(f"   First frame: {FIRST_FRAME_IMAGE}")
        if has_last_frame:
            print(f"   Last frame:  {LAST_FRAME_IMAGE}")

        operation = client.models.generate_videos(
            model=MODEL,
            prompt=PROMPT,
            image=first_image,
            config=config,
        )

        operation = _poll_until_done(client, operation)

        for vid_idx, gen_video in enumerate(operation.response.generated_videos):
            final_output = OUTPUT_PATH
            if NUMBER_OF_VIDEOS > 1:
                base, ext = os.path.splitext(OUTPUT_PATH)
                final_output = f"{base}_{vid_idx + 1}{ext}"

            print(f"   📥 Downloading to {final_output}…")
            client.files.download(file=gen_video.video)
            gen_video.video.save(final_output)
            print(f"   ✅ Saved: {os.path.abspath(final_output)}")
            video_ids.append(final_output)

    else:
        # ── Pure Text-to-Video Mode ──
        print(f"\n{'─' * 50}")
        print(f"🎬 Text-to-Video generation")

        config = types.GenerateVideosConfig(
            aspect_ratio=ASPECT_RATIO,
            resolution=RESOLUTION,
            number_of_videos=NUMBER_OF_VIDEOS,
        )

        print(f"   Model:      {MODEL}")
        print(f"   Aspect:     {ASPECT_RATIO}")
        print(f"   Resolution: {RESOLUTION}")
        print(f"   Prompt:     {PROMPT[:80]}{'…' if len(PROMPT) > 80 else ''}")

        operation = client.models.generate_videos(
            model=MODEL,
            prompt=PROMPT,
            config=config,
        )

        operation = _poll_until_done(client, operation)

        for vid_idx, gen_video in enumerate(operation.response.generated_videos):
            final_output = OUTPUT_PATH
            if NUMBER_OF_VIDEOS > 1:
                base, ext = os.path.splitext(OUTPUT_PATH)
                final_output = f"{base}_{vid_idx + 1}{ext}"

            print(f"   📥 Downloading to {final_output}…")
            client.files.download(file=gen_video.video)
            gen_video.video.save(final_output)
            print(f"   ✅ Saved: {os.path.abspath(final_output)}")
            video_ids.append(final_output)

    # ── Final Summary ──
    print(f"\n{'═' * 50}")
    print(f"🏁 Workflow Complete")
    print(f"   Total Videos: {len(video_ids)}")
    for v in video_ids:
        print(f"   • {v}")
    print(f"{'═' * 50}\n")

    return video_ids


if __name__ == "__main__":
    generate_video()
