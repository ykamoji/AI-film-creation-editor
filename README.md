# 🎬 AI Film Creation Editor

A modular Python toolkit for AI-powered video generation, editing, and management. Provides parallel workflows for both **OpenAI Sora 2** and **Google Veo 3.1**, enabling you to generate cinematic video clips from text prompts and reference images.

---

## Features

| Capability | Sora (OpenAI) | Veo (Google) |
|---|:---:|:---:|
| Text-to-video generation | ✅ | ✅ |
| Reference image guidance (up to 14) | ✅ | ✅ |
| First / last frame control | — | ✅ |
| Video editing (style, color, lighting) | ✅ | — |
| Video extension (continue a clip) | ✅ | ✅ |
| Library management (list / view / delete) | ✅ | — |
| Native audio generation | — | ✅ |
| Portrait (9:16) & Landscape (16:9) | ✅ | ✅ |
| 720p / 1080p / 4K resolution | ✅ | ✅ |

---

## Project Structure

```
AI-film-creation-editor/
├── sora/                        # OpenAI Sora 2 workflows
│   ├── video_generate.py        #   Generate videos (text + up to 14 ref images)
│   ├── video_edit.py            #   Edit existing videos by video_id
│   ├── video_extend.py          #   Extend videos by additional seconds
│   └── video_library.py         #   CLI to list, view, download, delete videos
│
├── veo/                         # Google Veo 3.1 workflows
│   ├── video_generate.py        #   Generate videos (text + ref images + frames)
│   └── video_extend.py          #   Extend previously generated videos
│
├── main.py                      # Entry point placeholder
├── .env                         # API keys (not committed)
├── .gitignore
├── pyproject.toml               # Dependencies (uv / pip)
└── README.md
```

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd AI-film-creation-editor
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

Using **uv** (recommended):
```bash
uv sync
```

Or using **pip**:
```bash
pip install openai google-genai python-dotenv
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
# OpenAI (for Sora workflows)
OPENAI_API_KEY=sk-your-openai-key-here

# Google (for Veo workflows)
GEMINI_API_KEY=your-gemini-api-key-here
```

> **Note:** You only need the key for the provider you intend to use.

---

## Quick Start

### Generate a video with Sora

1. Open `sora/video_generate.py` and configure the variables at the top:
   - `PROMPT` — your scene description
   - `MODEL` — `"sora-2"` or `"sora-2-pro"`
   - `SIZE` — e.g. `"1280x720"`
   - `SECONDS` — `4`, `8`, or `12`
   - `INPUT_REFERENCE_IMAGES` — list of image paths (up to 14)
   - `OUTPUT_PATH` — where to save the MP4

2. Run:
   ```bash
   python sora/video_generate.py
   ```

### Generate a video with Veo

1. Open `veo/video_generate.py` and configure:
   - `PROMPT` — your scene description
   - `MODEL` — `"veo-3.1-generate-preview"` or `"veo-3.1-lite-generate-preview"`
   - `ASPECT_RATIO` — `"16:9"` or `"9:16"`
   - `RESOLUTION` — `"720p"`, `"1080p"`, or `"4k"`
   - `INPUT_REFERENCE_IMAGES` — list of image paths (up to 14)
   - `OUTPUT_PATH` — where to save the MP4

2. Run:
   ```bash
   python veo/video_generate.py
   ```

---

## Workflows

### 🎥 Sora — Video Generation (`sora/video_generate.py`)

Generates videos using OpenAI's Sora 2 model. Supports up to 14 reference images — each image is uploaded to the Files API and passed as an `input_reference` via the JSON body. When multiple images are provided, a separate video is generated per image.

**Configuration variables:**

| Variable | Description | Default |
|---|---|---|
| `PROMPT` | Text description of the video | *(see file)* |
| `MODEL` | `"sora-2"` or `"sora-2-pro"` | `"sora-2"` |
| `SIZE` | Resolution e.g. `"1280x720"` | `"1280x720"` |
| `SECONDS` | Duration: `4`, `8`, or `12` | `8` |
| `INPUT_REFERENCE_IMAGES` | List of image file paths (up to 14) | `[]` |
| `OUTPUT_PATH` | Output MP4 path | `"generated_video.mp4"` |
| `POLL_INTERVAL` | Seconds between status checks | `10` |

---

### ✂️ Sora — Video Editing (`sora/video_edit.py`)

Applies targeted modifications to an existing Sora video — color palette, lighting, weather, camera style — without regenerating from scratch.

**Configuration variables:**

| Variable | Description | Default |
|---|---|---|
| `VIDEO_ID` | ID of a completed Sora video | *(required)* |
| `PROMPT` | Description of the edit | *(see file)* |
| `OUTPUT_PATH` | Output MP4 path | `"edited_video.mp4"` |

```bash
python sora/video_edit.py
```

---

### 🔗 Sora — Video Extension (`sora/video_extend.py`)

Extends an existing Sora video by additional seconds, preserving motion and camera continuity. Each extension adds up to 20 seconds; a single video can be extended up to 6 times (max 120s total).

**Configuration variables:**

| Variable | Description | Default |
|---|---|---|
| `VIDEO_ID` | ID of a completed Sora video | *(required)* |
| `PROMPT` | Continuation description | *(see file)* |
| `SECONDS` | Seconds to add (max 20) | `10` |
| `OUTPUT_PATH` | Output MP4 path | `"extended_video.mp4"` |

```bash
python sora/video_extend.py
```

---

### 📚 Sora — Video Library (`sora/video_library.py`)

CLI tool for managing your Sora video library.

```bash
# List all videos
python sora/video_library.py list

# List with pagination
python sora/video_library.py list --limit 5 --order desc

# View details of a specific video
python sora/video_library.py view <VIDEO_ID>

# Download a completed video
python sora/video_library.py download <VIDEO_ID>

# Delete a video
python sora/video_library.py delete <VIDEO_ID>
```

---

### 🎬 Veo — Video Generation (`veo/video_generate.py`)

Generates videos using Google's Veo 3.1 model with native audio. Supports three generation modes:

1. **Text-to-video** — pure prompt-based generation
2. **Reference images** — up to 14 images batched into groups of 3 (API limit per request)
3. **Frame-based** — specify first frame, last frame, or both for interpolation

**Configuration variables:**

| Variable | Description | Default |
|---|---|---|
| `PROMPT` | Text description of the video | *(see file)* |
| `MODEL` | `"veo-3.1-generate-preview"` or `"veo-3.1-lite-generate-preview"` | `"veo-3.1-generate-preview"` |
| `ASPECT_RATIO` | `"16:9"` or `"9:16"` | `"16:9"` |
| `RESOLUTION` | `"720p"`, `"1080p"`, or `"4k"` | `"720p"` |
| `NUMBER_OF_VIDEOS` | Videos per request (1 or 2) | `1` |
| `INPUT_REFERENCE_IMAGES` | List of image paths (up to 14) | `[]` |
| `REFERENCE_TYPE` | `"subject"` (person) or `"asset"` (object) | `"asset"` |
| `FIRST_FRAME_IMAGE` | Path to opening frame image | `None` |
| `LAST_FRAME_IMAGE` | Path to closing frame image | `None` |
| `OUTPUT_PATH` | Output MP4 path | `"generated_video.mp4"` |

```bash
python veo/video_generate.py
```

---

### 🔗 Veo — Video Extension (`veo/video_extend.py`)

Extends a previously generated Veo video by 7 seconds per extension (up to 20 extensions, max 148s total). The extension continues motion, style, and audio.

**Limitations:**
- Only Veo-generated videos can be extended
- Input must be ≤141 seconds, 720p, 16:9 or 9:16
- Videos expire after 2 days (referencing resets the timer)

**Configuration variables:**

| Variable | Description | Default |
|---|---|---|
| `PREVIOUS_OPERATION_NAME` | Operation name from a prior generation | *(required)* |
| `PROMPT` | Continuation description | *(see file)* |
| `MODEL` | Must match the original model | `"veo-3.1-generate-preview"` |
| `RESOLUTION` | Limited to `"720p"` | `"720p"` |
| `OUTPUT_PATH` | Output MP4 path | `"extended_video.mp4"` |

```bash
python veo/video_extend.py
```

---

## How It Works

All workflows follow the same async pattern:

```
Configure → Submit job → Poll for completion → Download MP4
```

1. **Configure** — Edit the variables at the top of each script
2. **Submit** — The script sends the request to the API and receives a job/operation ID
3. **Poll** — A progress loop checks the status every N seconds until `completed` or `failed`
4. **Download** — The finished video is saved to the specified output path

---

## Reference Images

### Sora
The Sora API accepts **1 reference image per request** via the `input_reference` parameter. When you provide multiple images, the script generates a separate video for each one. Images are uploaded to the Files API and passed as a JSON `file_id` reference.

### Veo
The Veo API accepts **up to 3 reference images per request** via the `reference_images` config. When you provide more than 3 (up to 14), the script automatically batches them into groups of 3 and generates one video per batch. Each reference image is tagged with a `reference_type`:
- `"subject"` — for people or characters (preserves facial features)
- `"asset"` — for objects, clothing, or products

---

## API Specifications

### Sora 2

| Parameter | Supported Values |
|---|---|
| Models | `sora-2`, `sora-2-pro` |
| Sizes | `480x480`, `1024x576`, `576x1024`, `1280x720`, `720x1280`, `1920x1080`, `1080x1920` |
| Duration | `4s`, `8s`, `12s` |
| Max extensions | 6 per video (max 120s total) |
| Image formats | JPEG, PNG, WebP |

### Veo 3.1

| Parameter | Supported Values |
|---|---|
| Models | `veo-3.1-generate-preview`, `veo-3.1-lite-generate-preview` |
| Aspect ratios | `16:9`, `9:16` |
| Resolutions | `720p`, `1080p`, `4k` (4k not available for Lite) |
| Duration | 8-second clips |
| Max extensions | 20 per video (up to 148s total) |
| Ref images per request | Up to 3 |
| Image formats | JPEG, PNG, WebP |
| Native audio | ✅ (Veo 3.1 only) |

---

## Requirements

- Python 3.11+
- **OpenAI API Key** — for Sora workflows ([get one here](https://platform.openai.com/account/api-keys))
- **Gemini API Key** — for Veo workflows ([get one here](https://aistudio.google.com/apikey))

### Python Dependencies

```
openai>=2.36.0
google-genai>=2.2.0
python-dotenv>=1.2.2
```

---

## License

See [LICENSE](LICENSE) for details.
