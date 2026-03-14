---
name: ocr
description: OCR and document text extraction with PaddleOCR-VL GGUF via llama-cpp-python. Use when the user asks to read text from images/screenshots/scans, parse tables from image files, or run local vision OCR inference with ModelScope model `megemini/PaddleOCR-VL-1.5-GGUF`.
homepage: https://modelscope.cn/models/megemini/PaddleOCR-VL-1.5-GGUF
metadata: {"nanobot":{"emoji":"👁️"}}
---

# OCR (PaddleOCR-VL GGUF)

Use this skill to run one-shot local OCR with `PaddleOCR-VL-1.5-GGUF` from ModelScope via `llama-cpp-python`.

## Quick Start

Run OCR for one image (auto-download model from ModelScope if needed):

```bash
python3 scripts/paddleocr_vl_ocr.py --image /path/to/image.png
```

Use explicit local GGUF files:

```bash
python3 scripts/paddleocr_vl_ocr.py \
  --image /path/to/image.png \
  --model-path /models/PaddleOCR-VL-0.9B-Q4_K_M.gguf \
  --mmproj-path /models/PaddleOCR-VL-0.9B-mmproj-f16.gguf
```

Multiple images in one run (model loads once):

```bash
python3 scripts/paddleocr_vl_ocr.py \
  --image img1.png img2.jpg img3.png
```

Skip auto-download (require explicit paths):

```bash
python3 scripts/paddleocr_vl_ocr.py \
  --skip-download \
  --model-path /models/model.gguf \
  --mmproj-path /models/mmproj.gguf \
  --image /path/to/image.png
```

## What the Script Does

`scripts/paddleocr_vl_ocr.py` will:
1. Download `megemini/PaddleOCR-VL-1.5-GGUF` from ModelScope (unless `--model-path` and `--mmproj-path` are provided or `--skip-download` is set).
2. Auto-detect model GGUF and mmproj GGUF from the snapshot directory.
3. Load the model once via `llama-cpp-python` with `Llava15ChatHandler`.
4. Run OCR on each image and print extracted text to stdout.

## Common Options

- `--image`: One or more image paths (required).
- `--prompt`: OCR instruction prompt (default: extract all visible text in reading order).
- `--max-tokens`: Max generated tokens (default: `4096`).
- `--repo-id`: ModelScope repo ID (default: `megemini/PaddleOCR-VL-1.5-GGUF`).
- `--revision`: Optional ModelScope revision.
- `--download-dir`: Model cache directory (default: `~/.cache/modelscope`).
- `--model-path` / `--mmproj-path`: Explicit GGUF file paths.
- `--model-glob` / `--mmproj-glob`: Glob patterns to select specific GGUF files from snapshot.
- `--skip-download`: Disable auto-download, require `--model-path` and `--mmproj-path`.
- `--ctx-size`: Context length (default: `16384`).
- `--n-gpu-layers`: Number of layers to offload to GPU (`-1` = all).
- `--n-threads`: Number of CPU threads for inference.
- `--temp`: Sampling temperature (default: `0.1`).
- `--verbose`: Enable verbose model loading and inference output.

## Dependencies

- Python package `llama-cpp-python`
- Python package `modelscope` (only needed for auto-download mode)

```bash
pip install llama-cpp-python modelscope
```

For more details, read:
- `references/paddleocr-vl-gguf.md`
