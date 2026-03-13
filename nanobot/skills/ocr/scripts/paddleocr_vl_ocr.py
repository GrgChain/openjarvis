#!/usr/bin/env python3
"""One-shot OCR with PaddleOCR-VL GGUF via llama-cpp-python.

Loads the model once and runs OCR on one or more images,
avoiding per-image model reload overhead.
"""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path
from typing import Any


DEFAULT_REPO_ID = "megemini/PaddleOCR-VL-1.5-GGUF"
DEFAULT_PROMPT = (
    "Extract all visible text in reading order. "
    "Preserve line breaks and table structure when possible."
)


# ---------------------------------------------------------------------------
# Model discovery (unchanged from original)
# ---------------------------------------------------------------------------

def _load_modelscope_snapshot(repo_id: str, download_dir: Path, revision: str | None) -> Path:
    try:
        from modelscope import snapshot_download  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "modelscope is required for auto-download. Install with: pip install modelscope"
        ) from exc

    kwargs: dict[str, Any] = {"model_id": repo_id, "cache_dir": str(download_dir)}
    if revision:
        kwargs["revision"] = revision
    snapshot_path = snapshot_download(**kwargs)
    return Path(snapshot_path).resolve()


def _find_gguf_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.gguf") if p.is_file()]


def _select_mmproj(candidates: list[Path], mmproj_glob: str | None) -> Path:
    if mmproj_glob:
        matched = sorted([p for p in candidates if p.match(mmproj_glob)])
        if matched:
            return matched[0]

    mmproj_like = [
        p for p in candidates if "mmproj" in p.name.lower() or "projector" in p.name.lower()
    ]
    if not mmproj_like:
        raise FileNotFoundError("Cannot find mmproj gguf file in model directory")
    mmproj_like.sort(key=lambda p: (len(p.name), p.name))
    return mmproj_like[0]


def _select_model(candidates: list[Path], mmproj_path: Path, model_glob: str | None) -> Path:
    filtered = [
        p
        for p in candidates
        if p != mmproj_path
        and "mmproj" not in p.name.lower()
        and "projector" not in p.name.lower()
    ]
    if not filtered:
        raise FileNotFoundError("Cannot find model gguf file in model directory")

    if model_glob:
        glob_matched = [p for p in filtered if p.match(model_glob)]
        if glob_matched:
            glob_matched.sort(key=lambda p: p.stat().st_size, reverse=True)
            return glob_matched[0]

    preferred = [p for p in filtered if "q4" in p.name.lower()]
    if preferred:
        preferred.sort(key=lambda p: p.stat().st_size, reverse=True)
        return preferred[0]

    filtered.sort(key=lambda p: p.stat().st_size, reverse=True)
    return filtered[0]


# ---------------------------------------------------------------------------
# Model loading & inference via llama-cpp-python
# ---------------------------------------------------------------------------

def _load_model(
    model_path: Path,
    mmproj_path: Path,
    ctx_size: int,
    n_gpu_layers: int | None,
    n_threads: int | None,
    verbose: bool = False,
) -> Any:
    """Load model using llama-cpp-python with Llava15ChatHandler for vision."""
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Llava15ChatHandler

    chat_handler = Llava15ChatHandler(
        clip_model_path=str(mmproj_path),
        verbose=verbose,
    )

    model = Llama(
        model_path=str(model_path),
        chat_handler=chat_handler,
        n_ctx=ctx_size,
        n_gpu_layers=n_gpu_layers or 0,
        n_threads=n_threads,
        logits_all=True,  # required for llava
        verbose=verbose,
    )
    return model


def _ocr_image(
    model: Any,
    image_path: Path,
    prompt: str,
    max_tokens: int,
    temp: float,
) -> str:
    """Run OCR on a single image using the loaded model."""
    image_bytes = image_path.read_bytes()
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    # Determine mime type
    suffix = image_path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }
    mime = mime_map.get(suffix, "image/png")
    data_url = f"data:{mime};base64,{b64}"

    result = model.create_chat_completion(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        max_tokens=max_tokens,
        temperature=temp,
    )

    choice = result["choices"][0]  # type: ignore
    return (choice.get("message", {}).get("content") or "").strip()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one-shot OCR with PaddleOCR-VL GGUF via llama-cpp-python."
    )
    parser.add_argument(
        "--image",
        nargs="+",
        required=True,
        help="One or more image paths.",
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="OCR prompt.")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Max generated tokens.")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID, help="ModelScope repo id.")
    parser.add_argument("--revision", default=None, help="Optional ModelScope revision.")
    parser.add_argument(
        "--download-dir",
        default=str(Path.home() / ".cache" / "modelscope"),
        help="ModelScope cache dir for snapshot_download.",
    )
    parser.add_argument("--model-path", default=None, help="Path to model GGUF.")
    parser.add_argument("--mmproj-path", default=None, help="Path to mmproj GGUF.")
    parser.add_argument(
        "--model-glob",
        default=None,
        help="Optional glob to select model GGUF from snapshot (example: '*Q4*.gguf').",
    )
    parser.add_argument(
        "--mmproj-glob",
        default=None,
        help="Optional glob to select mmproj GGUF from snapshot (example: '*mmproj*.gguf').",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Disable ModelScope auto-download and require --model-path/--mmproj-path.",
    )
    parser.add_argument("--ctx-size", type=int, default=16384, help="Context size.")
    parser.add_argument(
        "--n-gpu-layers",
        type=int,
        default=None,
        help="Number of layers to offload to GPU (-1 = all).",
    )
    parser.add_argument(
        "--n-threads",
        type=int,
        default=None,
        help="Number of CPU threads for inference.",
    )
    parser.add_argument("--temp", type=float, default=0.1, help="Sampling temperature.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose model loading and inference output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image_paths = [Path(p).expanduser().resolve() for p in args.image]
    for img in image_paths:
        if not img.exists():
            raise FileNotFoundError(f"Image not found: {img}")

    # --- Resolve model files ---
    model_path = Path(args.model_path).expanduser().resolve() if args.model_path else None
    mmproj_path = Path(args.mmproj_path).expanduser().resolve() if args.mmproj_path else None

    if not model_path or not mmproj_path:
        if args.skip_download:
            raise RuntimeError(
                "--skip-download is set, but --model-path/--mmproj-path are incomplete."
            )
        snapshot_root = _load_modelscope_snapshot(
            repo_id=args.repo_id,
            download_dir=Path(args.download_dir).expanduser().resolve(),
            revision=args.revision,
        )
        ggufs = _find_gguf_files(snapshot_root)
        if not ggufs:
            raise RuntimeError(f"No .gguf files found under snapshot: {snapshot_root}")
        if not mmproj_path:
            mmproj_path = _select_mmproj(ggufs, args.mmproj_glob)
        if not model_path:
            model_path = _select_model(ggufs, mmproj_path, args.model_glob)

    if not model_path.exists():
        raise FileNotFoundError(f"Model GGUF not found: {model_path}")
    if not mmproj_path.exists():
        raise FileNotFoundError(f"mmproj GGUF not found: {mmproj_path}")

    # --- Load model once ---
    print(f"Loading model: {model_path.name}", file=sys.stderr)
    print(f"Loading mmproj: {mmproj_path.name}", file=sys.stderr)
    model = _load_model(
        model_path=model_path,
        mmproj_path=mmproj_path,
        ctx_size=args.ctx_size,
        n_gpu_layers=args.n_gpu_layers,
        n_threads=args.n_threads,
        verbose=args.verbose,
    )
    print("Model loaded.", file=sys.stderr)

    # --- Run OCR on each image ---
    for idx, image_path in enumerate(image_paths, start=1):
        if len(image_paths) > 1:
            print(f"===== OCR {idx}/{len(image_paths)}: {image_path} =====")

        text = _ocr_image(
            model=model,
            image_path=image_path,
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            temp=args.temp,
        )
        print(text)

        if len(image_paths) > 1 and idx < len(image_paths):
            print()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise SystemExit(1)
