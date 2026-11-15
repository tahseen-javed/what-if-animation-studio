# Licences of QA tools (used on CI only, never shipped inside a video)

| Tool | Exact version / weights | Licence | Checked | Use |
|---|---|---|---|---|
| OpenCLIP code (`open_clip_torch`) | PyPI latest at run time, github.com/mlfoundations/open_clip | MIT (LICENSE text read on 2026-11-15; GitHub's detector shows NOASSERTION only because of the multi-name copyright line) | 2026-11-15 | Image embeddings for the set-distinctness check |
| OpenCLIP weights | `ViT-B-32`, pretrained `laion2b_s34b_b79k` (Hugging Face `laion/CLIP-ViT-B-32-laion2B-s34B-b79K`) | MIT (model card `license: mit`) | 2026-11-15 | Same; secondary note: trained on LAION-2B web images, used here only to measure our own frames, nothing is generated from it |
| torchvision ResNet-18 | `IMAGENET1K_V1` | BSD-3-Clause (torchvision) | 2026-11-15 | Secondary distance report only |
| faster-whisper | `small.en` (Systran) | MIT | 2026-11-15 | Voice vs script check |
| Chatterbox TTS | `chatterbox-tts` (Resemble AI) | MIT | 2026-11-15 | Narration (output carries Resemble's Perth watermark) |
