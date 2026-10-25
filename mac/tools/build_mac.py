"""Build portable Mousecape format 2.0 themes, writing only inside mac/."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import plistlib
import shutil
import subprocess
import sys
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent

# Identifiers are from the official Mousecape mousecloak/MCDefs.m cursorMap().
# The original diagonal1 clouds run NE-SW; diagonal2 runs NW-SE.
ROLE_SPECS = [
    ('com.apple.coregraphics.Arrow', '正常选择', 'normal'),
    ('com.apple.coregraphics.IBeam', '文本选择', 'text'),
    ('com.apple.coregraphics.IBeamXOR', '反色文本选择', 'text'),
    ('com.apple.coregraphics.Move', '移动', 'move'),
    ('com.apple.coregraphics.ArrowCtx', '上下文箭头', 'normal'),
    ('com.apple.coregraphics.Wait', '忙碌等待', 'busy'),
    ('com.apple.cursor.2', '链接选择', 'link'),
    ('com.apple.cursor.3', '不可用', 'unavailable'),
    ('com.apple.cursor.4', '后台运行', 'working'),
    ('com.apple.cursor.7', '精确选择', 'precision'),
    ('com.apple.cursor.8', '精确选择备用', 'precision'),
    ('com.apple.cursor.11', '抓取中', 'move'),
    ('com.apple.cursor.12', '可抓取', 'move'),
    ('com.apple.cursor.13', '指向链接', 'link'),
    ('com.apple.cursor.17', '向西调整', 'horizontal'),
    ('com.apple.cursor.18', '向东调整', 'horizontal'),
    ('com.apple.cursor.19', '水平调整', 'horizontal'),
    ('com.apple.cursor.20', '反色单元格选择', 'precision'),
    ('com.apple.cursor.21', '向北调整', 'vertical'),
    ('com.apple.cursor.22', '向南调整', 'vertical'),
    ('com.apple.cursor.23', '垂直调整', 'vertical'),
    ('com.apple.cursor.27', '窗口向东调整', 'horizontal'),
    ('com.apple.cursor.28', '窗口水平调整', 'horizontal'),
    ('com.apple.cursor.29', '窗口向东北调整', 'diagonal1'),
    ('com.apple.cursor.30', '窗口东北—西南调整', 'diagonal1'),
    ('com.apple.cursor.31', '窗口向北调整', 'vertical'),
    ('com.apple.cursor.32', '窗口垂直调整', 'vertical'),
    ('com.apple.cursor.33', '窗口向西北调整', 'diagonal2'),
    ('com.apple.cursor.34', '窗口西北—东南调整', 'diagonal2'),
    ('com.apple.cursor.35', '窗口向东南调整', 'diagonal2'),
    ('com.apple.cursor.36', '窗口向南调整', 'vertical'),
    ('com.apple.cursor.37', '窗口向西南调整', 'diagonal1'),
    ('com.apple.cursor.38', '窗口向西调整', 'horizontal'),
    ('com.apple.cursor.39', '多向调整', 'move'),
    ('com.apple.cursor.40', '帮助选择', 'alternate'),
    ('com.apple.cursor.41', '单元格选择', 'precision'),
]


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def import_source_assets():
    """Read the Windows theme sources; copy editable assets into this Mac package."""
    theme = json.loads((PARENT / 'theme.json').read_text(encoding='utf-8'))
    provenance = theme['artwork_provenance']
    (ROOT / 'assets').mkdir(exist_ok=True)
    source = {}
    for key, item in provenance.items():
        original = PARENT / 'assets' / f'{key}.png'
        target = ROOT / 'assets' / f'{key}.png'
        if 'crop' in item:
            left, top, right, bottom = item['crop']
            width, height = right - left, bottom - top
            side = max(width, height) + 8
            hotspot = [item['source_hotspot'][0] - left + (side - width) // 2,
                       item['source_hotspot'][1] - top + (side - height) // 2]
            size = [side, side]
        else:
            parent = 'vertical' if key == 'horizontal' else 'diagonal1'
            hotspot = source[parent]['hotspot']
            size = source[parent]['size']
        shutil.copyfile(original, target)
        with Image.open(target) as image:
            if list(image.size) != size:
                raise ValueError(f'Unexpected source image size: {key}')
        source[key] = {'file': target.relative_to(ROOT).as_posix(), 'size': size,
                       'hotspot': hotspot, 'origin': 'Existing This Dog transparent artwork'}
    redraw = PARENT / 'editable' / 'normal_redrawn.png'
    if redraw.is_file():
        target = ROOT / 'assets' / 'normal_redrawn.png'
        shutil.copyfile(redraw, target)
        source['normal_redrawn'] = dict(source['normal'], file='assets/normal_redrawn.png',
                                        origin='Existing hand-edited vector redraw')
        (ROOT / 'editable').mkdir(exist_ok=True)
        shutil.copyfile(PARENT / 'editable' / 'normal_redrawn.svg', ROOT / 'editable' / 'normal_redrawn.svg')
    write_json(ROOT / 'source_assets.json', source)
    return source


def make_cursor(asset, points, cache):
    key = (asset['file'], points)
    if key in cache:
        return cache[key]
    with Image.open(ROOT / asset['file']) as original:
        image = original.convert('RGBA')
        representations = []
        for factor in (1, 2):
            buffer = io.BytesIO()
            image.resize((points * factor, points * factor), Image.Resampling.LANCZOS).save(
                buffer, format='PNG')
            representations.append(buffer.getvalue())
    result = {
        'FrameCount': 1,
        'FrameDuration': 1.0,
        'HotSpotX': asset['hotspot'][0] * points / asset['size'][0],
        'HotSpotY': asset['hotspot'][1] * points / asset['size'][1],
        'PointsWide': float(points),
        'PointsHigh': float(points),
        'Representations': representations,
    }
    cache[key] = result
    return result


def make_zip():
    """Package a self-contained copy, with no Windows executables or parent paths."""
    target = ROOT / '这狗_mac.zip'
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(ROOT.rglob('*')):
            if not path.is_file() or path == target or '__pycache__' in path.parts:
                continue
            archive.write(path, (Path('这狗_mac') / path.relative_to(ROOT)).as_posix())
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP integrity check failed')
        if any('..' in Path(name).parts or name.startswith('/') for name in archive.namelist()):
            raise ValueError('ZIP contains an unsafe member path')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-assets', action='store_true', help='Refresh PNGs from the adjacent Windows source theme')
    args = parser.parse_args()
    ROOT.mkdir(exist_ok=True)
    source_path = ROOT / 'source_assets.json'
    assets = import_source_assets() if args.refresh_assets or not source_path.exists() else json.loads(
        source_path.read_text(encoding='utf-8'))
    roles = {identifier: {'name': name, 'asset': asset} for identifier, name, asset in ROLE_SPECS}
    themes = [
        {'file': '这狗_mac.cape', 'name': '这狗 · Mac 标准', 'identifier': 'local.thisdog.macos.standard', 'points': 32, 'arrow_asset': 'normal'},
        {'file': '这狗_mac_大号.cape', 'name': '这狗 · Mac 大号', 'identifier': 'local.thisdog.macos.large', 'points': 48, 'arrow_asset': 'normal'},
    ]
    for number, label in enumerate(('耳机', '甜筒', '抱抱', '表情', '张嘴'), 1):
        themes.append({'file': f'备选/这狗_mac_备选{number}_{label}.cape', 'name': f'这狗 · Mac {label}',
                       'identifier': f'local.thisdog.macos.alternative{number}', 'points': 32,
                       'arrow_asset': f'extra{number}'})
    if 'normal_redrawn' in assets:
        themes.append({'file': '备选/这狗_mac_矢量重绘.cape', 'name': '这狗 · Mac 矢量重绘',
                       'identifier': 'local.thisdog.macos.vector', 'points': 32, 'arrow_asset': 'normal_redrawn'})
    cache = {}
    for spec in themes:
        cursors = {}
        for identifier, item in roles.items():
            key = spec['arrow_asset'] if identifier == 'com.apple.coregraphics.Arrow' else item['asset']
            cursors[identifier] = make_cursor(assets[key], spec['points'], cache)
        cape = {
            'Author': '这狗主题适配；原展示图：你自己做吧',
            'CapeName': spec['name'],
            'CapeVersion': 1.0,
            'Cloud': False,
            'HiDPI': True,
            'Identifier': spec['identifier'],
            'MinimumVersion': 2.0,
            'Version': 2.0,
            'Cursors': cursors,
        }
        path = ROOT / spec['file']
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(plistlib.dumps(cape, fmt=plistlib.FMT_XML, sort_keys=False))
        spec['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        'name': '这狗 · Mac / Mousecape', 'format': 'Mousecape plist 2.0',
        'static': True, 'scales': [1, 2], 'themes': themes, 'roles': roles, 'assets': assets,
        'source_url': 'https://www.xiaohongshu.com/discovery/item/696b5835000000000e00c7a4',
        'format_sources': [
            'https://github.com/alexzielenski/Mousecape/blob/master/Mousecape/com.maxrudberg.svanslosbluehazard.cape',
            'https://github.com/alexzielenski/Mousecape/blob/master/Mousecape/mousecloak/MCDefs.m',
            'https://github.com/alexzielenski/Mousecape/blob/master/Mousecape/mousecloak/apply.m',
        ],
        'unmapped': 'Other macOS cursor roles and application-defined cursors retain their own appearance. No exact macOS equivalents for Windows handwriting/pin/person roles.',
        'runtime_test': 'Generated and structurally verified on Windows; not applied on macOS hardware.',
    }
    write_json(ROOT / 'manifest.json', manifest)
    preview = ROOT / 'tools' / 'create_preview.py'
    if preview.exists():
        subprocess.run([sys.executable, '-B', str(preview)], check=True)
    verify = subprocess.run([sys.executable, '-B', str(ROOT / 'tools' / 'verify_mac.py'), str(ROOT)],
                            capture_output=True, text=True, encoding='utf-8')
    if verify.returncode:
        raise RuntimeError(verify.stdout + '\n' + verify.stderr)
    report = json.loads(verify.stdout)
    write_json(ROOT / '验证结果.json', report)
    make_zip()
    print(json.dumps({'themes': len(themes), 'roles_per_theme': len(roles), 'retina_scales': [1, 2],
                      'root': str(ROOT), 'zip': '这狗_mac.zip'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
