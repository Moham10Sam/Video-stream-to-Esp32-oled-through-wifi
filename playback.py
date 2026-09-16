"""
playback_wifi.py — Stream a preprocessed .bin frame file to an ESP32 over
WiFi (TCP), paced to the original video's fps using a fixed wall-clock
origin so timing error doesn't accumulate over the clip.

Usage:
    python playback_wifi.py output.bin 192.168.1.42 3333

The IP is printed by the ESP32 sketch over Serial on boot (open Arduino
IDE's Serial Monitor once, after flashing, to read it). Port must match
TCP_PORT in the sketch (default 3333).

Protocol per frame: 2 sync bytes [0xAA, 0x55] + 1024 payload bytes
"""

import sys
import json
import time
import socket

FRAME_BYTES = 1024
SYNC = bytes([0xAA, 0x55])


def main():
    if len(sys.argv) != 4:
        print("Usage: python playback_wifi.py frames.bin <esp32_ip> <port>")
        sys.exit(1)

    bin_path, ip, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
    sidecar_path = bin_path.rsplit(".", 1)[0] + ".json"

    with open(sidecar_path) as f:
        meta = json.load(f)
    fps = meta["fps"]
    frame_count = meta["frame_count"]

    print(f"Connecting to {ip}:{port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # don't batch small writes, send frames promptly
    print("Connected.")

    with open(bin_path, "rb") as f:
        data = f.read()

    if len(data) != frame_count * FRAME_BYTES:
        print("Warning: file size doesn't match sidecar frame_count — check preprocess output.")

    start_time = time.time()
    for i in range(frame_count):
        offset = i * FRAME_BYTES
        payload = data[offset: offset + FRAME_BYTES]

        target_time = start_time + i / fps
        delay = target_time - time.time()
        if delay > 0:
            time.sleep(delay)

        sock.sendall(SYNC + payload)

        if i % 50 == 0:
            print(f"\rframe {i}/{frame_count}", end="", flush=True)

    print(f"\nDone streaming {frame_count} frames.")
    sock.close()


if __name__ == "__main__":
    main()