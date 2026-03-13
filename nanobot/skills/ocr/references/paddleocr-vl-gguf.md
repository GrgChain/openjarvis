# PaddleOCR-VL GGUF Notes

## Model

- ModelScope repo: `megemini/PaddleOCR-VL-1.5-GGUF`
- URL: https://modelscope.cn/models/megemini/PaddleOCR-VL-1.5-GGUF

## Runtime

This skill uses `llama-cpp-python` with `Llava15ChatHandler` for multimodal GGUF inference.
The model and mmproj are loaded once and reused for all images.

Typical Python usage:

```python
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler

handler = Llava15ChatHandler(clip_model_path="/path/to/mmproj.gguf")
model = Llama(
    model_path="/path/to/model.gguf",
    chat_handler=handler,
    n_ctx=16384,
    logits_all=True,
)
result = model.create_chat_completion(messages=[...])
```

## Python Dependencies

```bash
pip install llama-cpp-python
```

Auto-download mode also requires:

```bash
pip install modelscope
```

## Troubleshooting

- `Cannot find mmproj gguf`: pass `--mmproj-path` explicitly.
- `No .gguf files found`: verify the ModelScope repo content/download permission.
- `logits_all=True` is required for Llava-based vision inference.
- If running out of memory, try a smaller quantization or reduce `--ctx-size`.
