"""Encode and inspect transparent Windows cursors without changing system settings.

``build_cur`` accepts a Pillow image and a hotspot in its original pixel
coordinates.  Each requested size receives a square, transparent canvas; the
source image is fitted and centered without changing its aspect ratio.
"""

from __future__ import annotations

import operator
from pathlib import Path
import struct
import sys
from typing import Any, Sequence

from PIL import Image

__all__ = ["build_cur", "inspect_cur", "validate_windows"]

DEFAULT_SIZES = (32, 48, 64, 96, 128)
_CUR_HEADER = struct.Struct("<HHH")
_CUR_ENTRY = struct.Struct("<BBBBHHII")
_DIB_HEADER = struct.Struct("<IiiHHIIiiII")


def _checked_sizes(sizes: Sequence[int]) -> tuple[int, ...]:
    result = []
    for value in sizes:
        if isinstance(value, bool):
            raise ValueError("Cursor sizes must be integers from 1 through 256.")
        try:
            size = operator.index(value)
        except TypeError as exc:
            raise ValueError("Cursor sizes must be integers from 1 through 256.") from exc
        if not 1 <= size <= 256:
            raise ValueError("Cursor sizes must be integers from 1 through 256.")
        result.append(size)
    if not result or len(result) != len(set(result)):
        raise ValueError("Provide at least one size, with no duplicate sizes.")
    return tuple(result)


def _checked_hotspot(hotspot: tuple[int, int], width: int, height: int) -> tuple[int, int]:
    if len(hotspot) != 2:
        raise ValueError("The hotspot must contain exactly two pixel coordinates.")
    try:
        if any(isinstance(value, bool) for value in hotspot):
            raise TypeError
        x, y = (operator.index(value) for value in hotspot)
    except TypeError as exc:
        raise ValueError("Hotspot coordinates must be integers.") from exc
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError("The hotspot must lie inside the source image.")
    return x, y


def _sized_image(
    image: Image.Image, hotspot: tuple[int, int], size: int
) -> tuple[Image.Image, tuple[int, int]]:
    scale = size / max(image.size)
    width = max(1, min(size, round(image.width * scale)))
    height = max(1, min(size, round(image.height * scale)))
    offset_x, offset_y = (size - width) // 2, (size - height) // 2
    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # Pasting without a mask preserves the image's original alpha values.
    canvas.paste(resized, (offset_x, offset_y))
    # Map pixel centers, then select the nearest destination pixel center.
    x = min(width - 1, int((hotspot[0] + 0.5) * width / image.width)) + offset_x
    y = min(height - 1, int((hotspot[1] + 0.5) * height / image.height)) + offset_y
    return canvas, (x, y)


def _dib_bytes(image: Image.Image) -> bytes:
    width, height = image.size
    rgba = image.tobytes("raw", "RGBA")
    xor_bitmap = bytearray(width * height * 4)
    mask_stride = ((width + 31) // 32) * 4
    and_mask = bytearray(mask_stride * height)
    for y in range(height):
        bottom_row = height - 1 - y
        for x in range(width):
            source = (y * width + x) * 4
            dest = (bottom_row * width + x) * 4
            r, g, b, alpha = rgba[source : source + 4]
            if alpha == 0:
                # Zero RGB prevents color fringes in viewers that ignore alpha.
                and_mask[bottom_row * mask_stride + x // 8] |= 0x80 >> (x % 8)
            else:
                xor_bitmap[dest : dest + 4] = bytes((b, g, r, alpha))
    header = _DIB_HEADER.pack(
        40, width, height * 2, 1, 32, 0,
        len(xor_bitmap) + len(and_mask), 0, 0, 0, 0,
    )
    return header + xor_bitmap + and_mask


def build_cur(
    image: Image.Image,
    hotspot: tuple[int, int],
    sizes: tuple[int, ...] = DEFAULT_SIZES,
) -> bytes:
    """Return a multi-resolution CUR encoded as BGRA DIBs plus AND masks.

    ``hotspot`` is an integer ``(x, y)`` inside the source image.  The source is
    converted to RGBA, fitted to each square canvas, and centered.  Hotspots use
    the same fitting transform.  The function does not write any files.
    """
    if not isinstance(image, Image.Image):
        raise TypeError("image must be a Pillow Image.Image.")
    if image.width <= 0 or image.height <= 0:
        raise ValueError("The source image must not be empty.")
    checked_sizes = _checked_sizes(sizes)
    checked_hotspot = _checked_hotspot(hotspot, image.width, image.height)
    rgba = image.convert("RGBA")
    offset = _CUR_HEADER.size + _CUR_ENTRY.size * len(checked_sizes)
    entries, resources = [], []
    for size in checked_sizes:
        frame, frame_hotspot = _sized_image(rgba, checked_hotspot, size)
        resource = _dib_bytes(frame)
        entries.append(_CUR_ENTRY.pack(
            size % 256, size % 256, 0, 0,
            frame_hotspot[0], frame_hotspot[1], len(resource), offset,
        ))
        resources.append(resource)
        offset += len(resource)
    return (
        _CUR_HEADER.pack(0, 2, len(checked_sizes))
        + b"".join(entries)
        + b"".join(resources)
    )


def inspect_cur(data: bytes) -> dict[str, Any]:
    """Parse 32-bit uncompressed DIB CUR data into JSON-serializable metadata.

    This pure function performs no filesystem or Windows API operations.
    Invalid headers, truncated resources, overlapping resources, and unsupported
    image encodings raise ``ValueError``.  Alpha/mask agreement is reported as
    metadata so a structurally valid third-party cursor can also be inspected.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be a bytes-like object.")
    data = bytes(data)
    if len(data) < _CUR_HEADER.size:
        raise ValueError("Truncated CUR header.")
    reserved, kind, count = _CUR_HEADER.unpack_from(data)
    if reserved != 0 or kind != 2 or count == 0:
        raise ValueError("Expected a nonempty CUR file (reserved=0, type=2).")
    directory_end = _CUR_HEADER.size + count * _CUR_ENTRY.size
    if directory_end > len(data):
        raise ValueError("Truncated CUR directory.")
    images, resource_ranges = [], []
    for index in range(count):
        fields = _CUR_ENTRY.unpack_from(data, _CUR_HEADER.size + index * _CUR_ENTRY.size)
        width_byte, height_byte, color_count, entry_reserved, hot_x, hot_y, length, offset = fields
        width, height = width_byte or 256, height_byte or 256
        if entry_reserved != 0 or not (hot_x < width and hot_y < height):
            raise ValueError(f"Invalid directory fields or hotspot in image {index}.")
        if offset < directory_end or length < _DIB_HEADER.size or offset + length > len(data):
            raise ValueError(f"Invalid resource range in image {index}.")
        for previous_start, previous_end in resource_ranges:
            if offset < previous_end and offset + length > previous_start:
                raise ValueError("CUR image resources overlap.")
        resource_ranges.append((offset, offset + length))
        if data[offset : offset + 8] == b"\x89PNG\r\n\x1a\n":
            raise ValueError("PNG-compressed CUR images are not supported by this inspector.")
        dib = _DIB_HEADER.unpack_from(data, offset)
        header_size, dib_width, doubled_height, planes, bits, compression, image_size, _, _, colors_used, _ = dib
        if header_size != 40 or planes != 1 or bits != 32 or compression != 0:
            raise ValueError(f"Image {index} must use a 40-byte, 32-bit BI_RGB DIB header.")
        if dib_width != width or doubled_height != height * 2:
            raise ValueError(f"Directory and DIB dimensions differ in image {index}.")
        if color_count != 0 or colors_used != 0:
            raise ValueError(f"Unexpected color table in 32-bit image {index}.")
        mask_stride = ((width + 31) // 32) * 4
        xor_size, mask_size = width * height * 4, mask_stride * height
        expected_length = header_size + xor_size + mask_size
        if length != expected_length or image_size not in (0, xor_size, xor_size + mask_size):
            raise ValueError(f"Inconsistent DIB byte lengths in image {index}.")
        pixels_offset, mask_offset = offset + header_size, offset + header_size + xor_size
        transparent = partial = masked = 0
        alpha_mask_consistent, transparent_rgb_zero = True, True
        for bottom_row in range(height):
            for x in range(width):
                pixel = pixels_offset + (bottom_row * width + x) * 4
                alpha = data[pixel + 3]
                mask_bit = bool(data[mask_offset + bottom_row * mask_stride + x // 8] & (0x80 >> (x % 8)))
                transparent += alpha == 0
                partial += 0 < alpha < 255
                masked += mask_bit
                alpha_mask_consistent &= mask_bit == (alpha == 0)
                if alpha == 0:
                    transparent_rgb_zero &= data[pixel : pixel + 3] == b"\0\0\0"
        images.append({
            "index": index,
            "width": width,
            "height": height,
            "hotspot": [hot_x, hot_y],
            "encoding": "BGRA_DIB",
            "bit_count": bits,
            "offset": offset,
            "resource_size": length,
            "and_mask_stride": mask_stride,
            "transparent_pixels": transparent,
            "partial_alpha_pixels": partial,
            "visible_pixels": width * height - transparent,
            "masked_pixels": masked,
            "alpha_mask_consistent": bool(alpha_mask_consistent),
            "transparent_rgb_zero": bool(transparent_rgb_zero),
        })
    return {"type": "CUR", "size_bytes": len(data), "image_count": count, "images": images}


def validate_windows(
    path: str | Path, sizes: tuple[int, ...] = DEFAULT_SIZES
) -> dict[str, Any]:
    """Load requested CUR sizes with Windows and verify dimensions/hotspots.

    The result is JSON serializable, including on non-Windows platforms or
    failure.  Each requested size must have an exact directory entry.  Handles
    allocated by LoadImageW/GetIconInfo are released in ``finally`` blocks.
    No API that changes the active pointer or system settings is used.
    """
    result: dict[str, Any] = {
        "path": str(Path(path).resolve()),
        "platform": sys.platform,
        "available": sys.platform == "win32",
        "valid": False,
        "checks": [],
        "errors": [],
    }
    try:
        checked_sizes = _checked_sizes(sizes)
        inspection = inspect_cur(Path(path).read_bytes())
        result["inspection"] = inspection
    except (OSError, TypeError, ValueError) as exc:
        result["errors"].append(str(exc))
        return result
    if sys.platform != "win32":
        result["errors"].append("Windows cursor loading APIs are unavailable on this platform.")
        return result

    import ctypes
    from ctypes import wintypes

    class ICONINFO(ctypes.Structure):
        _fields_ = [
            ("fIcon", wintypes.BOOL),
            ("xHotspot", wintypes.DWORD),
            ("yHotspot", wintypes.DWORD),
            ("hbmMask", wintypes.HANDLE),
            ("hbmColor", wintypes.HANDLE),
        ]

    class BITMAP(ctypes.Structure):
        _fields_ = [
            ("bmType", wintypes.LONG),
            ("bmWidth", wintypes.LONG),
            ("bmHeight", wintypes.LONG),
            ("bmWidthBytes", wintypes.LONG),
            ("bmPlanes", wintypes.WORD),
            ("bmBitsPixel", wintypes.WORD),
            ("bmBits", ctypes.c_void_p),
        ]

    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        user32.LoadImageW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ICONINFO)]
        user32.GetIconInfo.restype = wintypes.BOOL
        user32.DestroyCursor.argtypes = [wintypes.HANDLE]
        user32.DestroyCursor.restype = wintypes.BOOL
        gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
        gdi32.GetObjectW.restype = ctypes.c_int
        gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
        gdi32.DeleteObject.restype = wintypes.BOOL
    except (AttributeError, OSError) as exc:
        result["errors"].append(str(exc))
        return result

    def api_error(api: str) -> str:
        code = ctypes.get_last_error()
        return f"{api} failed with Win32 error {code}: {ctypes.FormatError(code).strip()}"

    def bitmap_info(handle: int) -> dict[str, int]:
        bitmap = BITMAP()
        if not gdi32.GetObjectW(handle, ctypes.sizeof(bitmap), ctypes.byref(bitmap)):
            raise OSError(api_error("GetObjectW"))
        return {"width": bitmap.bmWidth, "height": abs(bitmap.bmHeight), "bit_count": bitmap.bmBitsPixel * bitmap.bmPlanes}

    for size in checked_sizes:
        expected = next((entry for entry in inspection["images"] if entry["width"] == size and entry["height"] == size), None)
        check: dict[str, Any] = {
            "requested_size": [size, size],
            "expected_hotspot": expected["hotspot"] if expected else None,
            "loaded": False,
            "valid": False,
            "errors": [],
            "cleanup": {},
        }
        if expected is None:
            check["errors"].append("No exact CUR directory entry exists for the requested size.")
        cursor = None
        info = ICONINFO()
        try:
            ctypes.set_last_error(0)
            cursor = user32.LoadImageW(None, result["path"], 2, size, size, 0x0010)
            if not cursor:
                raise OSError(api_error("LoadImageW"))
            check["loaded"] = True
            ctypes.set_last_error(0)
            if not user32.GetIconInfo(cursor, ctypes.byref(info)):
                raise OSError(api_error("GetIconInfo"))
            check["is_cursor"] = not bool(info.fIcon)
            check["hotspot"] = [int(info.xHotspot), int(info.yHotspot)]
            check["hotspot_matches"] = expected is not None and check["hotspot"] == expected["hotspot"]
            if info.hbmColor:
                check["color_bitmap"] = bitmap_info(info.hbmColor)
                actual_size = [check["color_bitmap"]["width"], check["color_bitmap"]["height"]]
            elif info.hbmMask:
                monochrome = bitmap_info(info.hbmMask)
                actual_size = [monochrome["width"], monochrome["height"] // 2]
            else:
                raise OSError("GetIconInfo returned no cursor bitmap.")
            if info.hbmMask:
                check["mask_bitmap"] = bitmap_info(info.hbmMask)
            check["actual_size"] = actual_size
            check["size_matches"] = actual_size == [size, size]
            check["hotspot_in_bounds"] = 0 <= info.xHotspot < actual_size[0] and 0 <= info.yHotspot < actual_size[1]
            check["valid"] = all((check["is_cursor"], check["size_matches"], check["hotspot_matches"], check["hotspot_in_bounds"]))
        except (OSError, ValueError) as exc:
            check["errors"].append(str(exc))
        finally:
            for name, handle in (("color_bitmap_deleted", info.hbmColor), ("mask_bitmap_deleted", info.hbmMask)):
                if handle:
                    released = bool(gdi32.DeleteObject(handle))
                    check["cleanup"][name] = released
                    if not released:
                        check["errors"].append(f"Failed to release {name.removesuffix('_deleted')}.")
                        check["valid"] = False
            if cursor:
                released = bool(user32.DestroyCursor(cursor))
                check["cleanup"]["cursor_destroyed"] = released
                if not released:
                    check["errors"].append("Failed to destroy the loaded cursor.")
                    check["valid"] = False
        result["checks"].append(check)
    result["valid"] = bool(result["checks"]) and all(check["valid"] for check in result["checks"])
    return result
