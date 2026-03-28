"""
Run this once to generate PNG icons for the Chrome extension:
    python extension/generate_icons.py
"""
import struct, zlib, os

def _png(size, bg=(35, 134, 54), dark=(13, 17, 23)):
    """Generate a simple rounded-square PNG icon in GitHub green."""
    r = max(2, size // 6)          # corner radius (pixel approximation)
    pixels = []
    for y in range(size):
        row = []
        for x in range(size):
            # Round corners by checking distance from each corner
            in_tl = x < r and y < r and (x - r) ** 2 + (y - r) ** 2 > r ** 2
            in_tr = x >= size - r and y < r and (x - (size - r - 1)) ** 2 + (y - r) ** 2 > r ** 2
            in_bl = x < r and y >= size - r and (x - r) ** 2 + (y - (size - r - 1)) ** 2 > r ** 2
            in_br = x >= size - r and y >= size - r and (x - (size - r - 1)) ** 2 + (y - (size - r - 1)) ** 2 > r ** 2
            if in_tl or in_tr or in_bl or in_br:
                row.extend(dark)
            else:
                # Inner "IQ" dot pattern for larger icons
                cx, cy = size // 2, size // 2
                dot_r = max(2, size // 8)
                if size >= 48 and (x - cx) ** 2 + (y - cy) ** 2 <= dot_r ** 2:
                    row.extend([255, 255, 255])   # white centre dot
                else:
                    row.extend(bg)
        pixels.append(bytes(row))

    raw = b''.join(b'\x00' + row for row in pixels)
    compressed = zlib.compress(raw, 9)

    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    png  = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', ihdr)
    png += chunk(b'IDAT', compressed)
    png += chunk(b'IEND', b'')
    return png


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "icons")
    os.makedirs(out, exist_ok=True)
    for size in (16, 48, 128):
        path = os.path.join(out, f"icon{size}.png")
        with open(path, "wb") as f:
            f.write(_png(size))
        print(f"Created {path}")
    print("Done — icons ready for Chrome extension.")
