"""
preprocess.py — Convert a video into a raw .bin stream of SSD1306-format
128x64 monochrome frames, ready to be streamed to an ESP32 over Bluetooth.

Output frame format matches Adafruit_SSD1306's internal buffer layout exactly:
  - 8 "pages" (rows of 8 pixels each), 128 bytes per page = 1024 bytes/frame
  - within a page, bit 0 (LSB) = top pixel, bit 7 (MSB) = bottom pixel
This means the ESP32 side can just memcpy() the bytes into the display
buffer with zero per-pixel processing.

Usage:
    python preprocess.py input_video.mp4 output.bin

Produces:
    output.bin        raw binary, frames back-to-back, 1024 bytes each
    output.json        sidecar: {"fps": .., "frame_count": .., "width":128,"height":64}
"""

import sys
import json
import numpy as np
import cv2
from PIL import Image

WIDTH, HEIGHT = 128, 64
FRAME_BYTES = (WIDTH * HEIGHT) // 8  # 1024

# precompute bit weights for packing: shape (1,8,1) -> broadcast over (page, bitrow, col)
_WEIGHTS = (1 << np.arange(8, dtype=np.uint8)).reshape(1, 8, 1)


def pack_ssd1306(bilevel_arr: np.ndarray) -> bytes:
    """bilevel_arr: (64,128) bool/uint8 array, True/1 = pixel ON (lit)."""
    pages = bilevel_arr.reshape(8, 8, WIDTH).astype(np.uint8)  # (page, bitrow, col)
    byte_page = (pages * _WEIGHTS).sum(axis=1).astype(np.uint8)  # (8,128)
    return byte_page.tobytes()  # 1024 bytes, page-major then column


def frame_to_bilevel(frame_bgr: np.ndarray) -> np.ndarray:
    """Resize + dither a BGR frame to 128x64 bool array, True = lit pixel."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb).resize((WIDTH, HEIGHT), Image.LANCZOS)
    # convert('1') uses Floyd-Steinberg dithering by default — much better
    # than a flat threshold for real video content.
    dithered = img.convert("L").convert("1")
    arr = np.array(dithered)  # 0 or 255, shape (64,128)
    return arr > 0


def main():
    if len(sys.argv) != 3:
        print("Usage: python preprocess.py input_video.mp4 output.bin")
        sys.exit(1)

    in_path, out_path = sys.argv[1], sys.argv[2]
    sidecar_path = out_path.rsplit(".", 1)[0] + ".json"

    cap = cv2.VideoCapture(in_path)
    if not cap.isOpened():
        print(f"Could not open {in_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frame_count = 0
    with open(out_path, "wb") as out:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            bilevel = frame_to_bilevel(frame)
            out.write(pack_ssd1306(bilevel))
            frame_count += 1
            if frame_count % 50 == 0:
                print(f"\r{frame_count}/{total} frames", end="", flush=True)

    cap.release()
    print(f"\nDone. {frame_count} frames written to {out_path}")

    with open(sidecar_path, "w") as f:
        json.dump(
            {"fps": fps, "frame_count": frame_count, "width": WIDTH, "height": HEIGHT},
            f,
            indent=2,
        )
    print(f"Sidecar written to {sidecar_path}")


if __name__ == "__main__":
    main()