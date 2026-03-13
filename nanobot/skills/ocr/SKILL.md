---
name: ocr
description: OCR and document text extraction with PaddleOCR-VL GGUF via llama.cpp. Use when the user asks to read text from images/screenshots/scans, parse tables from image files, or run local vision OCR inference with ModelScope model `megemini/PaddleOCR-VL-1.5-GGUF`.
homepage: https://modelscope.cn/models/megemini/PaddleOCR-VL-1.5-GGUF
metadata: {"nanobot":{"emoji":"👁️"}}
---

# OCR (PaddleOCR-VL GGUF)

Use this skill to run one-shot local OCR with `PaddleOCR-VL-1.5-GGUF` from ModelScope.

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

Pass through extra llama-cli flags:

```bash
python3 scripts/paddleocr_vl_ocr.py \
  --image /path/to/image.png \
  --extra-arg --no-display-prompt \
  --extra-arg --simple-io
```

## What the Script Does

`scripts/paddleocr_vl_ocr.py` will:
1. Download `megemini/PaddleOCR-VL-1.5-GGUF` from ModelScope (unless files are provided).
2. Auto-detect model GGUF and mmproj GGUF.
3. Run `llama-cli` directly for each image (no server lifecycle).
4. Print OCR text to stdout.

## Common Options

- `--image`: One or more image paths.
- `--prompt`: OCR instruction prompt.
- `--repo-id`: ModelScope repo ID (default: `megemini/PaddleOCR-VL-1.5-GGUF`).
- `--download-dir`: Model cache directory.
- `--model-path` / `--mmproj-path`: Explicit GGUF paths.
- `--llama-cli-bin`: llama.cpp CLI binary (default: `llama-cli`).
- `--ctx-size`: Context length passed to llama-cli (default: `16384`).
- `--n-gpu-layers`: Optional `-ngl` value for llama.cpp.
- `--extra-arg`: Extra raw args passed to llama-cli.

## Dependencies

- `llama-cli` from `llama.cpp`
- Python package `modelscope` (only needed for auto-download mode)

For installation notes, read:
- `references/paddleocr-vl-gguf.md`
