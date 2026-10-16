# Training a road-damage detector for CivicLens

The shipped YOLO weights are COCO-pretrained (`yolov8n.pt`): they contain
no `pothole` / `crack` classes, so `PotholeDetector.detect()` legitimately
returns zero YOLO hits and the classical Canny fallback carries detection
(precision ~0.29, recall ~0.50 on the synthetic demo route — see
`python eval/eval_detector.py`). **Do not quote pothole accuracy for the
COCO weights.** This guide lists exactly what is needed to train, plug in,
and validate a real road-damage checkpoint.

## 1. Data needed

- **Images:** dashcam frames at the deployment resolution (960px wide
  minimum), covering day, night, rain glare, and motion blur. RDD2020
  (India split) is the reference open set; supplement with fleet footage
  from the target ward.
- **Labels:** YOLO-format `*.txt` per image (`class cx cy w h`, normalized),
  classes `0 = pothole`, `1 = crack`. Every hole in
  `eval/datasets/demo-route/labels.json` needs a box; crack boxes are
  currently **zero** — the eval reports `crack: unevaluated` until they exist.
- **Splits:** train/val/test by *route segment*, not by frame (adjacent
  frames leak). Report day/night/rain splits separately — the PRD targets
  are P>=0.75 / R>=0.65 per split.
- **Negatives:** speed breakers, tar patches, lane paint, manholes as
  background or explicit negative class (see `eval/failure_cases/README.md`
  §3–4 for why).

## 2. Training (reference command)

```bash
# Ultralytics, GPU host (not the 2GB demo box)
yolo detect train model=yolov8n.pt data=rdd2020.yaml epochs=100 imgsz=960 \
  conf=0.25 iou=0.5
# Expected artifact: runs/detect/train/weights/best.pt
```

Any YOLOv8-compatible checkpoint works (`best.pt`, ONNX, TensorRT engine).

## 3. Plugging the checkpoint in

```yaml
# config.yaml
detection:
  weights: "runs/rdd/yolov8n-rdd.pt"  # path or hub id; wins over `model`
  model: "yolov8n"                     # legacy hub shorthand (COCO)
  conf_threshold: 0.25
  classes: [pothole, crack]            # must intersect the checkpoint's names
```

- A missing explicit `weights` file raises `FileNotFoundError` at detector
  startup with this remediation (fail fast, not silent zero-detection).
- When the checkpoint's class names do not overlap `classes` (e.g. COCO
  weights), the detector logs a warning and YOLO contributes nothing —
  classical fallback carries detection until retrained.
- The 2GB demo box cannot load torch/YOLO alongside the API; it runs
  `agent/demo_worker.py` (classical-only) by design. Full fusion runs on
  the vision worker image.

## 4. Validating

```bash
python eval/eval_detector.py   # per-class + per-condition P/R (classical shown; YOLO needs the checkpoint)
python eval/eval_dedup.py      # precision/recall + duplicate rate + false tickets per route
python eval/eval_severity.py   # rank agreement vs engineer order
```

Quote only numbers these scripts print on your hardware and data.
Throughput reference: YOLOv8n ~356 ms/frame on ARM (see `docs/PERF.md`;
rerun `make bench` before quoting).
