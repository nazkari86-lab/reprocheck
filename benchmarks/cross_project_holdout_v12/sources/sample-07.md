# VisionTrack

> **Real-time multi-stream person detection, tracking, and counting system for smart city surveillance**

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF.svg)](https://github.com/ultralytics/ultralytics)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![CUDA](https://img.shields.io/badge/CUDA-Enabled-76B900.svg)](https://developer.nvidia.com/cuda-toolkit)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Overview

VisionTrack is a proof-of-concept intelligent surveillance system designed for smart city deployment. Built for city councils and operators who need to monitor crowd density across multiple public spaces (parks, transit stations, shopping districts) in real time — without requiring technical expertise.

The system simultaneously ingests multiple camera feeds, identifies and tracks individuals using YOLOv8 and ByteTrack, counts entries and exits across configurable Regions of Interest (ROIs), and raises alerts when crowd thresholds are exceeded.

**Demo:** `reports/demo_results/multi_stream_demo.mp4`

---

## Features

### Detection & Tracking
- **YOLOv8** person detection with confidence threshold control
- **ByteTrack** (via supervision) for persistent entity tracking across frames
- Unique ID assignment preserved across occlusions and re-entries
- Configurable detection confidence (0.10 – 0.75)

### Multi-Stream Analysis
- Simultaneous processing of multiple video feeds
- Interleaved frame scheduling — no stream blocks another
- Independent ID namespaces per stream (no cross-stream ID collisions)
- Per-stream telemetry and alerting

### Region-of-Interest (ROI) Analytics
- Automatic ROI line generation based on frame geometry
- Directional counting — distinguishes ingress from egress
- Live entity-in-zone tracking with crowd density alerts

### Performance Optimization
- **ONNX-quantized** model for 2–4× inference speedup
- **CUDA** GPU acceleration with automatic CPU fallback
- Frame skipping strategy for multi-stream load balancing
- Threaded OpenCV + OMP parallelism tuning

### Dashboard
- Clean Palantir-inspired operator interface
- Live FPS, average FPS, latency, ingress, egress, and zone occupancy
- Toggleable detection / tracking / counting modules per stream
- Crowd-breach alerts with configurable density thresholds

---

## Architecture

```
┌───────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ Video Stream  │───▶│  YOLOv8     │───▶│  ByteTrack   │───▶│  ROI        │
│ (mp4/avi/mov) │    │  Detection  │    │  Tracking    │    │  Counter    │
└───────────────┘    └─────────────┘    └──────────────┘    └─────────────┘
                            │                    │                   │
                            └────────────────────▼───────────────────┘
                                                 │
                                         ┌───────▼────────┐
                                         │   Streamlit    │
                                         │   Dashboard    │
                                         └────────────────┘
```

---

## Project Structure

```
vision-track/
├── data/
│   ├── raw_videos/                   # Input video streams
│   ├── raw_images/                   # Sample imagery
│   └── coco_dataset/                 # Reference dataset
│
├── models/
│   ├── __init__.py
│   ├── yolo_person_detection.py      # YOLOv8 detector wrapper
│   └── checkpoints/
│       ├── best.pt                   # Trained PyTorch weights
│       ├── best_quantized.onnx       # ONNX-optimized weights
│       └── config.yaml               # Training/export config
│
├── utils/
│   ├── __init__.py
│   ├── data_loader.py                # Video/image loading
│   ├── preprocessing.py              # Resize, normalize, validate
│   ├── multi_stream_tracking_helpers.py  # ByteTrack integration
│   ├── counting_logic.py             # ROI counting logic
│   └── VisionTrack_Analysis.ipynb    # EDA + training notebook
│
├── reports/
│   ├── performance_metrics.json      # Evaluation metrics
│   └── demo_results/
│       ├── roi_counting_example.png  # ROI demo screenshot
│       └── multi_stream_demo.mp4     # Multi-stream demo video
│
├── logs/
│   └── app_errors.log                # Runtime error log
│
├── app.py                            # Streamlit dashboard
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

---

## Installation

### Prerequisites
- Python 3.10+
- NVIDIA GPU with CUDA 11.8+ (optional but recommended)
- 4GB+ RAM
- Webcam or video files for testing

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/vision-track.git
cd vision-track
```

### 2. Create a virtual environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify GPU (optional)

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

### 5. Launch the app

```bash
streamlit run app.py
```

The dashboard will open automatically at `http://localhost:8501`.

---

## Usage

1. **Launch the app** — `streamlit run app.py`
2. **Select feed(s)** — use the `SELECT FEED` uploader in the sidebar (single or multiple)
3. **Configure modules** — toggle Detection / Tracking / Zone Analytics on or off
4. **Tune parameters:**
   - `CONFIDENCE THRESHOLD` — minimum score for a detection (default 0.25)
   - `DENSITY ALERT LIMIT` — trigger crowd-breach alert at this count
5. **Monitor telemetry:**
   - **FPS** — instantaneous processing rate
   - **AVG FPS** — sustained throughput
   - **LATENCY MS** — per-frame processing time
   - **INGRESS / EGRESS** — directional counts across ROI
   - **IN ZONE** — current entities inside the ROI
6. **Red alert** triggers when in-zone count ≥ density threshold

---

## Performance

Benchmarked on 720p video · NVIDIA GeForce GTX 1660 Ti · Intel i7 CPU

| Metric | Threshold | Achieved | Status |
|--------|-----------|----------|--------|
| **Precision** | ≥ 0.85 | **0.92** | ✅ Pass |
| **Recall** | ≥ 0.80 | **0.90** | ✅ Pass |
| **F1 Score** | ≥ 0.85 | **0.91** | ✅ Pass |
| **Avg FPS (GPU)** | ≥ 15 | **35.5** | ✅ Pass |
| **Avg FPS (CPU)** | — | 13.8 | Fallback |
| **Latency (GPU)** | — | 28 ms | — |

Full metrics available at `reports/performance_metrics.json`.

---

## Model Pipeline

### Transfer Learning

- **Base:** YOLOv8n pretrained on COCO
- **Target class:** `person` (class 0)
- **Strategy:** Fine-tuned with a small learning rate (0.001) to preserve pretrained features
- **Epochs:** 10
- **Input:** 640×640

### Quantization

The trained PyTorch model is exported to ONNX format and served via ONNX Runtime for 2–4× inference speedup with negligible accuracy loss.

```bash
python utils/export_model.py
```

---

## GPU Acceleration

The app automatically detects CUDA availability:

```python
import torch
print("Using CUDA:", torch.cuda.is_available())
```

- **With GPU:** ~35 FPS per stream at 720p, batched inference
- **Without GPU:** ~14 FPS per stream, automatic CPU fallback

No code changes required — the same `app.py` runs on both.

---

## Error Handling

- Broken / corrupt video sources are caught and surface per-feed error messages without crashing the app.
- All exceptions are logged to `logs/app_errors.log` with timestamps and stack traces.
- Missing model weights, config files, or metrics fall back to safe defaults.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `ultralytics` | YOLOv8 detection |
| `supervision` | ByteTrack tracking, annotation |
| `streamlit` | Web dashboard |
| `opencv-python` | Video I/O, drawing |
| `torch` | Deep learning backend |
| `onnxruntime` | Quantized inference |
| `numpy`, `pandas` | Data utilities |
| `matplotlib` | Notebook visualizations |

Full list in `requirements.txt`.

---

## Validation Artifacts

All deliverables required by the project specification:

| Artifact | Location |
|----------|----------|
| Trained weights | `models/checkpoints/best.pt` |
| Quantized model | `models/checkpoints/best_quantized.onnx` |
| Model config | `models/checkpoints/config.yaml` |
| Performance report | `reports/performance_metrics.json` |
| ROI demo screenshot | `reports/demo_results/roi_counting_example.png` |
| Multi-stream demo | `reports/demo_results/multi_stream_demo.mp4` |
| Error log | `logs/app_errors.log` |
| Analysis notebook | `utils/VisionTrack_Analysis.ipynb` |

---

## Future Work

- Live RTSP / webcam stream support
- Multi-class detection (vehicles, bicycles)
- Heatmap visualization for long-term density patterns
- REST API for headless deployment
- Docker containerization

---

## License

MIT License — free to use for academic and commercial purposes.

---

## Author

**Salman Khamis** — [skhamis](https://learn.reboot01.com/git/skhamis)
Built for the **Reboot01** Bahrain AI Module.