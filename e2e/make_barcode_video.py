"""Erzeugt ein Y4M-Video mit einem EAN-13-Barcode als Ersatz für die Kamera in Chromium
(--use-file-for-fake-video-capture). Keine Abhängigkeiten außer der Standardbibliothek.

Aufruf: python make_barcode_video.py 4006381333931 /pfad/barcode.y4m
"""

import sys

L = ["0001101", "0011001", "0010011", "0111101", "0100011",
     "0110001", "0101111", "0111011", "0110111", "0001011"]  # fmt: skip
G = ["0100111", "0110011", "0011011", "0100001", "0011101",
     "0111001", "0000101", "0010001", "0001001", "0010111"]  # fmt: skip
R = ["1110010", "1100110", "1101100", "1000010", "1011100",
     "1001110", "1010000", "1000100", "1001000", "1110100"]  # fmt: skip
PARITY = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
          "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"]  # fmt: skip


def ean13_modules(code: str) -> str:
    assert len(code) == 13 and code.isdigit()
    first, left, right = int(code[0]), code[1:7], code[7:]
    bits = "101"
    for digit, parity in zip(left, PARITY[first], strict=True):
        bits += (L if parity == "L" else G)[int(digit)]
    bits += "01010"
    bits += "".join(R[int(d)] for d in right)
    return bits + "101"


def main(code: str, out: str, width=640, height=480, module=4, frames=10) -> None:
    bits = ean13_modules(code)
    bar_w = len(bits) * module
    x0, y0, y1 = (width - bar_w) // 2, height // 2 - 90, height // 2 + 90
    row_bar = bytearray([235] * width)
    for i, b in enumerate(bits):
        if b == "1":
            row_bar[x0 + i * module : x0 + (i + 1) * module] = bytes([16] * module)
    blank = bytes([235] * width)
    y_plane = b"".join(bytes(row_bar) if y0 <= y < y1 else blank for y in range(height))
    chroma = bytes([128] * (width // 2 * height // 2))
    with open(out, "wb") as f:
        f.write(f"YUV4MPEG2 W{width} H{height} F10:1 Ip A1:1 C420jpeg\n".encode())
        for _ in range(frames):
            f.write(b"FRAME\n" + y_plane + chroma + chroma)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
