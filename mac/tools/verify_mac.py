#!/usr/bin/env python3
"""Read-only structural and pixel verification of this Mousecape package.

Usage: python -B tools/verify_mac.py [package_directory]
Writes one JSON document to stdout and exits with status 1 on any failure.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import plistlib
import sys
from pathlib import Path

from PIL import Image


TOP_KEYS = {
    "Author", "CapeName", "CapeVersion", "Cloud", "HiDPI", "Identifier",
    "MinimumVersion", "Version", "Cursors",
}
CURSOR_KEYS = {
    "FrameCount", "FrameDuration", "HotSpotX", "HotSpotY", "PointsWide",
    "PointsHigh", "Representations",
}
# Official MCDefs.m cursorMap(): numeric IDs 2-5 and 7-43 (6 is absent).
OFFICIAL_IDS = {
    "com.apple.coregraphics." + name
    for name in (
        "Arrow", "IBeam", "IBeamXOR", "Alias", "Copy", "Move", "ArrowCtx",
        "Wait", "Empty",
    )
} | {"com.apple.cursor." + str(i) for i in (*range(2, 6), *range(7, 44))}


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def is_positive_integer(value):
    return is_number(value) and value > 0 and int(value) == value


def contained_path(root, value):
    if not isinstance(value, str) or not value:
        raise ValueError("file must be a nonempty relative path")
    path = Path(value)
    if path.is_absolute():
        raise ValueError("absolute file path is not allowed")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("file path escapes the package directory")
    return resolved


def png_image(data, label):
    """Fully decode PNG bytes without converting away mode information."""
    if not isinstance(data, bytes):
        raise ValueError(label + ": expected plist Data bytes")
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR" or data[24:26] != b"\x08\x06":
        raise ValueError(label + ": expected PNG IHDR with 8-bit channels and RGBA color type")
    with Image.open(io.BytesIO(data)) as header:
        if header.format != "PNG":
            raise ValueError(label + ": representation is not PNG")
        header.verify()
    with Image.open(io.BytesIO(data)) as opened:
        opened.load()
        if opened.mode != "RGBA":
            raise ValueError(label + ": expected 32-bit RGBA, got " + opened.mode)
        decoded = opened.copy()
    minimum, maximum = decoded.getchannel("A").getextrema()
    if minimum != 0 or maximum <= 0:
        raise ValueError(label + ": expected fully transparent and visible pixels")
    return decoded


def verify_package(root):
    result = {
        "ok": False,
        "package": str(root),
        "scope": "plist schema, official role IDs, PNG pixels, dimensions, and hotspots; no macOS runtime test",
        "errors": [],
        "themes": [],
    }
    errors = result["errors"]
    if not root.is_dir():
        errors.append("Package directory does not exist")
        return result
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8-sig"))
        if not isinstance(manifest, dict):
            raise ValueError("manifest root is not a dictionary")
        themes, roles, assets = (manifest[key] for key in ("themes", "roles", "assets"))
        if not isinstance(themes, list) or not themes:
            raise ValueError("themes must be a nonempty list")
        if not isinstance(roles, dict) or not roles:
            raise ValueError("roles must be a nonempty dictionary")
        if not isinstance(assets, dict) or not assets:
            raise ValueError("assets must be a nonempty dictionary")
    except Exception as exc:
        errors.append("Cannot read manifest.json: " + str(exc))
        return result

    role_ids = set(roles)
    unknown_ids = role_ids - OFFICIAL_IDS
    if unknown_ids:
        errors.append("Unknown role IDs in manifest: " + ", ".join(sorted(unknown_ids)))
    for role_id, role in roles.items():
        if not isinstance(role, dict) or not isinstance(role.get("name"), str) or not isinstance(role.get("asset"), str):
            errors.append("Invalid role entry: " + role_id)
        elif role["asset"] not in assets:
            errors.append("Role references missing asset: " + role_id)

    decoded_assets = {}
    for asset_name, asset in assets.items():
        try:
            if not isinstance(asset, dict):
                raise ValueError("asset entry must be a dictionary")
            asset_path = contained_path(root, asset["file"])
            image = png_image(asset_path.read_bytes(), asset_name)
            size = asset["size"]
            hotspot = asset["hotspot"]
            if not isinstance(size, list) or len(size) != 2 or not all(is_positive_integer(v) for v in size):
                raise ValueError("size must contain two positive integer dimensions")
            if tuple(size) != image.size:
                raise ValueError("PNG dimensions differ from manifest size")
            if not isinstance(hotspot, list) or len(hotspot) != 2 or not all(is_number(v) for v in hotspot):
                raise ValueError("hotspot must contain two finite numbers")
            if not all(0 <= hotspot[i] < size[i] for i in range(2)):
                raise ValueError("source hotspot is outside the source image")
            decoded_assets[asset_name] = (image, hotspot)
        except Exception as exc:
            errors.append("Asset " + asset_name + ": " + str(exc))

    declared_files = set()
    identifiers = set()
    for theme in themes:
        theme_result = {"file": theme.get("file") if isinstance(theme, dict) else None, "ok": False, "errors": []}
        result["themes"].append(theme_result)
        theme_errors = theme_result["errors"]
        try:
            if not isinstance(theme, dict):
                raise ValueError("theme entry must be a dictionary")
            cape_path = contained_path(root, theme["file"])
            if cape_path.suffix.lower() != ".cape":
                raise ValueError("theme file must end in .cape")
            if cape_path in declared_files:
                raise ValueError("theme file is declared more than once")
            declared_files.add(cape_path)
            points = theme["points"]
            if not is_positive_integer(points) or points not in (32, 48):
                raise ValueError("theme points must be 32 or 48")
            if theme["arrow_asset"] not in decoded_assets:
                raise ValueError("theme arrow_asset is absent or invalid")
            cape = plistlib.loads(cape_path.read_bytes())
            if not isinstance(cape, dict) or set(cape) != TOP_KEYS:
                raise ValueError("cape top-level keys differ from the official nine-key schema")
            for key in ("Author", "CapeName", "Identifier"):
                if not isinstance(cape[key], str) or not cape[key]:
                    raise ValueError(key + " must be a nonempty string")
            for key in ("Cloud", "HiDPI"):
                if not isinstance(cape[key], bool):
                    raise ValueError(key + " must be a plist Boolean")
            if not cape["HiDPI"]:
                raise ValueError("HiDPI must be true for the supplied 1x/2x images")
            if not is_number(cape["CapeVersion"]) or cape["CapeVersion"] <= 0:
                raise ValueError("CapeVersion must be positive numeric metadata")
            for key in ("MinimumVersion", "Version"):
                if not is_number(cape[key]) or cape[key] != 2.0:
                    raise ValueError(key + " must be format version 2.0")
            if cape["Identifier"] in identifiers:
                raise ValueError("cape Identifier is shared by more than one theme")
            identifiers.add(cape["Identifier"])
            cursors = cape["Cursors"]
            if not isinstance(cursors, dict) or set(cursors) != role_ids:
                raise ValueError("cape cursor IDs do not exactly match manifest roles")
            if set(cursors) - OFFICIAL_IDS:
                raise ValueError("cape uses unknown cursor IDs")

            representation_count = 0
            for role_id, cursor in cursors.items():
                try:
                    if not isinstance(cursor, dict) or set(cursor) != CURSOR_KEYS:
                        raise ValueError("cursor keys differ from the official seven-key schema")
                    if type(cursor["FrameCount"]) is not int or cursor["FrameCount"] != 1:
                        raise ValueError("FrameCount must be integer 1 for this static package")
                    if not is_number(cursor["FrameDuration"]) or cursor["FrameDuration"] <= 0:
                        raise ValueError("FrameDuration must be a positive number")
                    for key in ("PointsWide", "PointsHigh"):
                        if not is_positive_integer(cursor[key]) or cursor[key] != points:
                            raise ValueError(key + " must match the theme's 32 or 48 points")
                    for key in ("HotSpotX", "HotSpotY"):
                        if not is_number(cursor[key]) or not 0 <= cursor[key] < points:
                            raise ValueError(key + " must be a finite number inside the point dimensions")
                    role = roles[role_id]
                    asset_name = theme["arrow_asset"] if role_id == "com.apple.coregraphics.Arrow" else role["asset"]
                    source, source_hotspot = decoded_assets[asset_name]
                    for axis, key in enumerate(("HotSpotX", "HotSpotY")):
                        expected = source_hotspot[axis] * points / source.size[axis]
                        if abs(cursor[key] - expected) > 1e-6:
                            raise ValueError(key + " differs from source hotspot scaled into points")
                    reps = cursor["Representations"]
                    if not isinstance(reps, list) or len(reps) != 2:
                        raise ValueError("Representations must contain exactly 1x and 2x images")
                    scales = set()
                    for index, data in enumerate(reps):
                        image = png_image(data, "representation " + str(index))
                        if image.size == (points, points):
                            scale = 1
                        elif image.size == (points * 2, points * 2):
                            scale = 2
                        else:
                            raise ValueError("representation dimensions are neither 1x nor 2x")
                        if scale in scales:
                            raise ValueError("duplicate representation scale")
                        scales.add(scale)
                        expected_image = source.resize(image.size, Image.Resampling.LANCZOS)
                        if image.tobytes() != expected_image.tobytes():
                            raise ValueError("representation pixels differ from the LANCZOS-scaled source asset")
                        representation_count += 1
                    if scales != {1, 2}:
                        raise ValueError("both 1x and 2x representations are required")
                except Exception as exc:
                    theme_errors.append(role_id + ": " + str(exc))
            theme_result.update({
                "points": points,
                "arrow_asset": theme["arrow_asset"],
                "identifier": cape["Identifier"],
                "cursor_count": len(cursors),
                "representation_count": representation_count,
                "pixel_checks": "exact RGBA bytes against LANCZOS source resize",
                "hotspot_tolerance": 1e-6,
            })
        except Exception as exc:
            theme_errors.append(str(exc))
        theme_result["ok"] = not theme_errors

    actual_files = {path.resolve() for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".cape"}
    for path in sorted(actual_files - declared_files):
        errors.append("Undeclared cape: " + path.relative_to(root).as_posix())
    for path in sorted(declared_files - actual_files):
        errors.append("Declared cape is missing: " + path.relative_to(root).as_posix())
    result.update({
        "asset_count": len(assets),
        "validated_asset_count": len(decoded_assets),
        "role_count": len(roles),
        "cape_count": len(actual_files),
        "theme_count": len(themes),
        "ok": not errors and all(theme["ok"] for theme in result["themes"]),
    })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    try:
        result = verify_package(args.root.resolve())
    except Exception as exc:
        result = {"ok": False, "errors": [type(exc).__name__ + ": " + str(exc)]}
    # UTF-8 on Windows pipes, without creating output files or changing package state.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
