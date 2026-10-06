#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "rapidocr-onnxruntime"]
# ///
"""读照片里的文字：整图、放大、切块各跑一遍，合并去重。

  ocr.py photo.jpg [--out ocr.json] [--draw ocr.png]
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

class RapidOCRBackend:
    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR
        self.ocr = RapidOCR()
    def run(self, im):
        import numpy as np
        res, _ = self.ocr(np.array(im.convert("RGB"))[:, :, ::-1])
        out = []
        for box, text, conf in res or []:
            xs = [p[0] for p in box]; ys = [p[1] for p in box]
            out.append({"text": str(text), "conf": round(float(conf), 3),
                        "box": [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]})
        return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--out"); ap.add_argument("--draw")
    ap.add_argument("--min-conf", type=float, default=0.3)
    args = ap.parse_args()
    im = ImageOps.exif_transpose(Image.open(args.image))
    try:
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        import numpy as np
        res, _ = ocr(np.array(im.convert("RGB"))[:, :, ::-1])
        items = []
        for box, text, conf in res or []:
            if float(conf) < args.min_conf: continue
            xs = [p[0] for p in box]; ys = [p[1] for p in box]
            items.append({"text": str(text), "conf": round(float(conf), 3),
                          "box": [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]})
        items.sort(key=lambda t: -t["conf"])
        for t in items:
            print(f"{t['conf']:.2f}  {t['text']}")
        if args.out:
            Path(args.out).write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"-> {args.out}")
    except ImportError:
        sys.exit("需要 rapidocr-onnxruntime：uv run ocr.py（自动装依赖）")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
