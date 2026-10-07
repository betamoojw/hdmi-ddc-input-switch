"""Save the switch's info screen as a PNG (for docs, or to check a layout change).

    python tools/screenshot.py COM11 info-screen.png

Needs pyserial and Pillow. Close the web configurator first (it holds the port).
"""
import json
import sys

import serial
from PIL import Image


def grab(port, out):
    with serial.Serial(port, 115200, timeout=5) as s:
        s.reset_input_buffer()
        s.write(b'{"cmd":"screenshot"}\n')
        head = None
        while head is None:                      # skip key/boot events
            line = s.readline().decode(errors="replace").strip()
            if not line:
                raise SystemExit("no reply from the switch")
            if line.startswith("{"):
                msg = json.loads(line)
                if "w" in msg:
                    head = msg
        if not head.get("ok"):
            raise SystemExit("the switch has no video (DISABLE_VIDEO build?)")
        w, h = head["w"], head["h"]
        img = Image.new("1", (w, h))
        px = img.load()
        for y in range(h):
            line = s.readline().decode(errors="replace").strip()
            if not line.startswith("#") or len(line) != 1 + w // 4:
                raise ValueError(f"row {y} arrived damaged")
            row = bytes.fromhex(line[1:])
            for x in range(w):
                px[x, y] = (row[x // 8] >> (7 - x % 8)) & 1
    img.save(out)
    print(f"saved {out} ({w} x {h})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    for attempt in range(5):
        try:
            grab(sys.argv[1], sys.argv[2])
            break
        except ValueError as e:
            print(f"{e}, retrying")
    else:
        raise SystemExit("gave up after 5 tries")
