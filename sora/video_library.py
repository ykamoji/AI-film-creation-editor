"""
Video Library Manager
=====================
View, inspect, and delete videos from your OpenAI Sora library.

Usage:
    python video_library.py list                # List all videos
    python video_library.py list --limit 5      # List 5 videos
    python video_library.py view VIDEO_ID       # View details of a video
    python video_library.py delete VIDEO_ID     # Delete a video
    python video_library.py download VIDEO_ID   # Download a completed video

Environment variable:  OPENAI_API_KEY
"""

import os
import sys
import argparse
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────

# Default number of videos to list per page
DEFAULT_LIMIT = 20

# Sort order: "asc" or "desc"
DEFAULT_ORDER = "desc"

# Default download output filename pattern (video_id will be appended)
DOWNLOAD_DIR = "downloads"


# ── Helpers ────────────────────────────────────────────────────────────────

def _init_client():
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("ERROR: OPENAI_API_KEY environment variable is not set.")
    return OpenAI()


def _format_status(status):
    icons = {
        "completed": "✅",
        "failed": "❌",
        "queued": "🕐",
        "in_progress": "⏳",
    }
    return f"{icons.get(status, '❓')} {status}"


# ── Commands ───────────────────────────────────────────────────────────────

def cmd_list(args):
    """List videos in the library."""
    client = _init_client()
    limit = args.limit or DEFAULT_LIMIT
    order = args.order or DEFAULT_ORDER

    print(f"\n📚 Listing videos (limit={limit}, order={order})…\n")

    params = {"limit": limit, "order": order}
    if args.after:
        params["after"] = args.after

    videos = client.videos.list(**params)

    if not videos.data:
        print("  No videos found.")
        return

    print(f"  {'ID':<58} {'Status':<20} {'Model':<16} {'Size':<12} {'Sec':<5}")
    print(f"  {'─'*58} {'─'*20} {'─'*16} {'─'*12} {'─'*5}")

    for v in videos.data:
        vid = v.id
        status = _format_status(v.status)
        model = getattr(v, "model", "—") or "—"
        size = getattr(v, "size", "—") or "—"
        secs = getattr(v, "seconds", "—") or "—"
        print(f"  {vid:<58} {status:<20} {model:<16} {size:<12} {secs:<5}")

    print(f"\n  Total shown: {len(videos.data)}")
    if hasattr(videos, "has_more") and videos.has_more:
        last_id = videos.data[-1].id
        print(f"  More available — use: --after {last_id}")


def cmd_view(args):
    """View details of a specific video."""
    client = _init_client()
    video_id = args.video_id

    print(f"\n🔍 Retrieving video: {video_id}…\n")

    try:
        v = client.videos.retrieve(video_id)
    except Exception as e:
        sys.exit(f"❌ Could not retrieve video: {e}")

    print(f"  ID         : {v.id}")
    print(f"  Status     : {_format_status(v.status)}")
    print(f"  Model      : {getattr(v, 'model', '—')}")
    print(f"  Size       : {getattr(v, 'size', '—')}")
    print(f"  Seconds    : {getattr(v, 'seconds', '—')}")
    print(f"  Progress   : {getattr(v, 'progress', '—')}%")
    print(f"  Created At : {getattr(v, 'created_at', '—')}")

    if v.status == "failed":
        err = getattr(getattr(v, "error", None), "message", "Unknown")
        print(f"  Error      : {err}")


def cmd_delete(args):
    """Delete a video by ID."""
    client = _init_client()
    video_id = args.video_id

    print(f"\n🗑  Deleting video: {video_id}…")

    try:
        result = client.videos.delete(video_id)
        print(f"✅ Video deleted successfully.")
        if hasattr(result, "deleted"):
            print(f"   Confirmed: {result.deleted}")
    except Exception as e:
        sys.exit(f"❌ Failed to delete video: {e}")


def cmd_download(args):
    """Download a completed video."""
    client = _init_client()
    video_id = args.video_id

    print(f"\n📥 Downloading video: {video_id}…")

    try:
        v = client.videos.retrieve(video_id)
    except Exception as e:
        sys.exit(f"❌ Could not retrieve video: {e}")

    if v.status != "completed":
        sys.exit(f"❌ Video status is '{v.status}' — must be 'completed'.")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    output = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")

    content = client.videos.download_content(video_id, variant="video")
    content.write_to_file(output)
    print(f"✅ Saved to: {os.path.abspath(output)}")


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Manage your OpenAI Sora video library.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # list
    p_list = sub.add_parser("list", help="List videos in your library")
    p_list.add_argument("--limit", type=int, help=f"Max videos (default: {DEFAULT_LIMIT})")
    p_list.add_argument("--order", choices=["asc", "desc"], help="Sort order")
    p_list.add_argument("--after", type=str, help="Pagination cursor (video ID)")
    p_list.set_defaults(func=cmd_list)

    # view
    p_view = sub.add_parser("view", help="View details of a video")
    p_view.add_argument("video_id", help="The video ID to inspect")
    p_view.set_defaults(func=cmd_view)

    # delete
    p_del = sub.add_parser("delete", help="Delete a video")
    p_del.add_argument("video_id", help="The video ID to delete")
    p_del.set_defaults(func=cmd_delete)

    # download
    p_dl = sub.add_parser("download", help="Download a completed video")
    p_dl.add_argument("video_id", help="The video ID to download")
    p_dl.set_defaults(func=cmd_download)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
