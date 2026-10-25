"""Build the theme from the two downloaded reference sheets, without redrawing the dog."""
from pathlib import Path
import json
import sys
import base64
import io

import numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from cursor_codec import build_cur, inspect_cur, validate_windows

SIZES = (32, 48, 64, 96, 128)
SPECS = [
    ('normal', '正常选择', 2, (37, 426, 258, 641), (47, 441)),
    ('text', '文本选择', 2, (303, 418, 519, 636), (318, 461)),
    ('link', '链接选择', 2, (552, 424, 772, 635), (564, 436)),
    ('working', '后台运行', 2, (815, 437, 1040, 634), (827, 450)),
    ('move', '移动', 2, (64, 701, 267, 921), (164, 814)),
    ('vertical', '垂直调整', 2, (339, 698, 529, 928), (433, 815)),
    ('alternate', '候选', 2, (567, 702, 792, 919), (578, 714)),
    ('precision', '精确选择', 2, (822, 701, 1051, 923), (853, 733)),
    ('diagonal1', '对角线调整1', 2, (59, 985, 271, 1210), (165, 1100)),
    ('unavailable', '不可用', 2, (315, 993, 540, 1210), (348, 1025)),
    ('busy', '忙', 2, (575, 1000, 799, 1208), (685, 1111)),
    ('pen', '手写', 2, (811, 986, 1028, 1209), (862, 1000)),
    ('extra1', '备选1_耳机', 3, (110, 470, 337, 692), (121, 482)),
    ('extra2', '备选2_甜筒', 3, (420, 470, 644, 695), (432, 482)),
    ('extra3', '备选3_抱抱', 3, (728, 469, 965, 700), (741, 481)),
    ('extra4', '备选4_表情', 3, (265, 821, 492, 1040), (275, 834)),
    ('extra5', '备选5_张嘴', 3, (609, 831, 826, 1046), (620, 846)),
]


def extract(source, box, hotspot):
    """Remove the cyan sheet background; preserve closed interiors and edge alpha."""
    rgb = np.array(source.crop(box).convert('RGB')).astype(np.float64)
    border = np.concatenate([rgb[:3].reshape(-1, 3), rgb[-3:].reshape(-1, 3),
                             rgb[:, :3].reshape(-1, 3), rgb[:, -3:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    delta = np.linalg.norm(rgb - bg, axis=2)
    mask = delta > 11
    labels, count = ndi.label(mask)
    areas = ndi.sum(mask, labels, range(1, count + 1))
    largest = int(np.argmax(areas)) + 1
    for n in range(1, count + 1):
        component = labels == n
        clipped_label = n != largest and component[-3:].any() and component.sum() < areas[largest - 1] * .05
        if component.sum() < 7 or delta[component].max() < 30 or clipped_label:
            mask[component] = False
    mask = ndi.binary_fill_holes(mask)
    # Keep compression noise out, while preserving the original colored details.
    alpha = np.where(mask, np.clip((delta - 6) / 15, 0, 1), 0)
    alpha[ndi.binary_erosion(mask, iterations=1)] = 1
    solid = alpha > .98
    _, indices = ndi.distance_transform_edt(~solid, return_indices=True)
    foreground = rgb[indices[0], indices[1]]
    edge = (alpha > 0) & (alpha < .999)
    direction = foreground - bg
    estimated = np.sum((rgb - bg) * direction, axis=2) / np.maximum(
        np.sum(direction * direction, axis=2), 1)
    alpha[edge] = np.clip(estimated[edge], 0, 1)
    # Unmatte semitransparent pixels against the sheet color, preventing cyan halos.
    color = rgb.copy()
    color[edge] = (rgb[edge] - (1 - alpha[edge, None]) * bg) / np.maximum(alpha[edge, None], .01)
    color[alpha <= 0] = 0
    rgba = np.dstack([np.uint8(np.clip(color, 0, 255)), np.uint8(np.rint(alpha * 255))])
    image = Image.fromarray(rgba, 'RGBA')
    # Common square canvas makes resizing, preview and hotspots predictable.
    side = max(image.size) + 8
    square = Image.new('RGBA', (side, side))
    offset = ((side - image.width) // 2, (side - image.height) // 2)
    square.alpha_composite(image, offset)
    point = (hotspot[0] - box[0] + offset[0], hotspot[1] - box[1] + offset[1])
    return square, point


def resize_markers(image, diagonal=False):
    """Rotate the clouds around the dog; leave the character itself unchanged."""
    data = np.array(image)
    labels, count = ndi.label(data[:, :, 3] > 10)
    areas = ndi.sum(data[:, :, 3] > 10, labels, range(1, count + 1))
    dog_label = int(np.argmax(areas)) + 1
    cloud_ids = [n for n in range(1, count + 1) if n != dog_label and
                 np.all(data[labels == n, :3].mean(axis=0) > (225, 230, 230))]
    selected = np.isin(labels, cloud_ids)
    clouds = data.copy()
    clouds[~selected] = 0
    dog = data.copy()
    dog[selected] = 0
    marker = Image.fromarray(clouds).transpose(Image.Transpose.ROTATE_90)
    result = Image.fromarray(dog)
    result.alpha_composite(marker)
    return result


def font(size, bold=False):
    name = 'msyhbd.ttc' if bold else 'msyh.ttc'
    return ImageFont.truetype(str(Path('C:/Windows/Fonts') / name), size)


def previews(assets, mapping, files):
    width, height = 1280, 1190
    canvas = Image.new('RGB', (width, height), '#f3f8f7')
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((32, 28, 1248, 212), 28, fill='#d7eeea')
    d.text((64, 51), '这狗', font=font(52, True), fill='#193d3b')
    d.text((67, 124), '鼠标指针皮肤  /  原图提取静态版', font=font(24), fill='#426461')
    normal = assets['normal'][0].resize((160, 160), Image.Resampling.LANCZOS)
    canvas.paste(normal, (1020, 38), normal)
    order = [(s[0], s[1]) for s in SPECS[:12]] + [('horizontal', '水平调整'), ('diagonal2', '对角线调整2')]
    for i, (key, name) in enumerate(order):
        x, y = 40 + i % 7 * 172, 242 + i // 7 * 213
        d.rounded_rectangle((x, y, x + 162, y + 195), 18, fill='white')
        im = assets[key][0].resize((137, 137), Image.Resampling.LANCZOS)
        canvas.paste(im, (x + 13, y + 10), im)
        d.text((x + 81, y + 158), name, font=font(18), fill='#284844', anchor='mt')
    d.text((48, 694), '同图备选', font=font(25, True), fill='#193d3b')
    for i, spec in enumerate(SPECS[12:]):
        key, name = spec[:2]
        x, y = 48 + i * 188, 742
        im = assets[key][0].resize((160, 160), Image.Resampling.LANCZOS)
        canvas.paste(im, (x, y), im)
        d.text((x + 80, y + 167), name, font=font(18), fill='#284844', anchor='mt')
    d.rounded_rectangle((1025, 728, 1232, 963), 18, fill='#253635')
    canvas.paste(normal, (1046, 756), normal)
    d.text((1128, 928), '深色背景', font=font(18), fill='#ecf7f4', anchor='mt')
    d.line((48, 1005, 1232, 1005), fill='#c6dcd7', width=2)
    d.text((48, 1030), '32 / 48 / 64 / 96 / 128 px  ·  透明背景  ·  独立点击热点', font=font(24), fill='#426461')
    d.text((48, 1083), '17 个 Windows 角色 + 5 个备选；帮助、定位、人员角色复用已有造型。', font=font(19), fill='#607b77')
    d.text((48, 1124), '依据小红书展示图提取；不含作者原版动画。角色与原图归原作者所有。', font=font(19), fill='#607b77')
    canvas.save(ROOT / '预览.png')
    # Pixel-scale QA on white, dark and cyan backgrounds (without upscaling the sources).
    audit = Image.new('RGB', (720, len(assets) * 140), 'white')
    ad = ImageDraw.Draw(audit)
    for row, (key, (im, hot)) in enumerate(assets.items()):
        for col, bg in enumerate(('#ffffff', '#20282e', '#c9f2f1')):
            panel = Image.new('RGB', (240, 140), bg)
            small = im.resize((112, 112), Image.Resampling.LANCZOS)
            panel.paste(small, (64, 0), small)
            pd = ImageDraw.Draw(panel)
            pd.text((8, 114), key, font=font(15), fill='#7a8a88')
            audit.paste(panel, (240 * col, 140 * row))
    audit.save(ROOT / 'reference' / '透明边缘检查.png')


def demo_html(assets, mapping, files):
    assets, files = dict(assets), dict(files)
    choices = [(spec[0], spec[1]) for spec in SPECS] + [('horizontal', '水平调整'), ('diagonal2', '对角线调整2')]
    if (ROOT / 'editable' / 'normal_redrawn.png').is_file():
        assets['normal_redrawn'] = (Image.open(ROOT / 'editable' / 'normal_redrawn.png').convert('RGBA'), assets['normal'][1])
        files['normal_redrawn'] = 'editable/正常选择_矢量重绘.cur'
        choices.append(('normal_redrawn', '正常选择_矢量重绘'))
    cards = []
    for key, name in choices:
        relative = files[key]
        im, hot = assets[key]
        hx, hy = [round(p / im.width * 64) for p in hot]
        encoded = io.BytesIO()
        im.resize((64, 64), Image.Resampling.LANCZOS).save(encoded, format='PNG')
        data_url = 'data:image/png;base64,' + base64.b64encode(encoded.getvalue()).decode('ascii')
        cards.append(f'<button class="card" data-name="{name}" data-url="{data_url}" data-hot="{hx},{hy}" style="cursor:url(\'{relative}\'),auto"><img src="assets/{key}.png" alt="{name}"><span>{name}</span></button>')
    document = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>这狗 · 鼠标指针预览</title>
<style>*{box-sizing:border-box}body{margin:0;background:#eff7f4;color:#193d3b;font:16px/1.7 "Microsoft YaHei",sans-serif}main{max-width:1080px;margin:40px auto;padding:24px}header{display:flex;align-items:center;justify-content:space-between;background:#d5eeea;border-radius:28px;padding:28px 42px}h1{font-size:52px;margin:0}header img{width:156px}p{color:#577873}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px;margin:24px 0}.card{background:#fff;border:2px solid transparent;border-radius:18px;padding:10px 4px 18px;color:#264d48;font:inherit}.card:hover,.card:focus{border-color:#6aada3;outline:none}.card img{display:block;width:116px;height:116px;object-fit:contain;margin:auto}#play{padding:32px;border-radius:24px;background:#fff;min-height:210px;border:1px dashed #7caaa3}#play.dark{background:#243632;color:#eff7f4}.toolbar{display:flex;gap:14px;align-items:center;margin:20px 0}button,input,a{font:inherit}#dark{padding:8px 18px;border:0;border-radius:12px;background:#d5eeea;color:#193d3b}input{padding:10px;border:1px solid #b3d3cc;border-radius:8px;width:260px}footer{font-size:14px;margin-top:26px;color:#657c77}.dot{background:#d5eeea;border-radius:9px;padding:3px 9px}a{color:#31776b}</style>
<main><header><div><h1>这狗</h1><p>鼠标指针皮肤 · 原图提取静态版</p><span class="dot">17 个角色</span> <span class="dot">5 个备选</span></div><img src="assets/normal.png" alt="这狗"></header><p>鼠标移到卡片上预览原生光标；点击卡片后，在下方区域试用 64 像素版本。</p><div class="grid">CARDS</div><div class="toolbar"><strong id="selected">正常选择</strong><button id="dark">切换深 / 浅背景</button></div><section id="play"><p>在这里移动鼠标，检查指针轮廓与透明边缘。</p><input placeholder="这里可以测试文本输入" style="cursor:url('cursors/06_文本选择.cur'),text"> <a href="#play" style="cursor:url('cursors/15_链接选择.cur'),pointer">这里可以测试链接选择</a></section><footer>Windows：双击“应用这狗.cmd”。它会在当前文件夹内备份原方案，并直接引用这里的文件。使用期间请保留整个文件夹。<br>只需单个指针：在 Windows 鼠标属性 → 指针 → 正常选择 → 浏览，选择 cursors/01_正常选择.cur。<br>素材来源：小红书“你自己做吧”的这狗指针展示图。本版保留展示图造型；没有取得原作者的原始动画光标。水平与另一方向的对角线调整仅调整云朵方向；部分系统角色复用图中造型。</footer></main>
<script>const area=document.querySelector('#play');document.querySelectorAll('.card').forEach(card=>card.addEventListener('click',()=>{const [x,y]=card.dataset.hot.split(',');area.style.cursor=`url("${card.dataset.url}") ${x} ${y},auto`;document.querySelector('#selected').textContent=card.dataset.name;}));document.querySelector('#dark').addEventListener('click',()=>area.classList.toggle('dark'));document.querySelector('.card').click();</script></html>'''
    document = document.replace('</style>', '#play.dark p{color:#bfd8d3}#play.dark a{color:#b6e3d8}</style>')
    document = document.replace('CARDS', ''.join(cards)).replace('src="assets/normal_redrawn.png"', 'src="editable/normal_redrawn.png"')
    (ROOT / '预览.html').write_text(document, encoding='utf-8')


def main():
    for directory in ('assets', 'cursors', 'alternatives', 'reference'):
        (ROOT / directory).mkdir(exist_ok=True)
    sources = {n: Image.open(ROOT / 'reference' / f'reference_{n:02}.webp') for n in (2, 3)}
    assets, origins = {}, {}
    for key, name, source, box, hotspot in SPECS:
        assets[key] = extract(sources[source], box, hotspot)
        origins[key] = {'name': name, 'source': f'reference/reference_{source:02}.webp',
                        'crop': box, 'source_hotspot': hotspot, 'method': 'original sheet extraction'}
    assets['horizontal'] = (resize_markers(assets['vertical'][0]), assets['vertical'][1])
    assets['diagonal2'] = (resize_markers(assets['diagonal1'][0], True), assets['diagonal1'][1])
    for key in ('horizontal', 'diagonal2'):
        origins[key] = {'method': 'cloud markers rotated 90 degrees; original dog unchanged'}
    roles = [
        ('Arrow', '正常选择', 'normal'), ('Help', '帮助选择', 'alternate'),
        ('AppStarting', '后台运行', 'working'), ('Wait', '忙', 'busy'),
        ('Crosshair', '精确选择', 'precision'), ('IBeam', '文本选择', 'text'),
        ('NWPen', '手写', 'pen'), ('No', '不可用', 'unavailable'),
        ('SizeNS', '垂直调整', 'vertical'), ('SizeWE', '水平调整', 'horizontal'),
        ('SizeNWSE', '对角线调整1', 'diagonal1'), ('SizeNESW', '对角线调整2', 'diagonal2'),
        ('SizeAll', '移动', 'move'), ('UpArrow', '候选', 'alternate'),
        ('Hand', '链接选择', 'link'), ('Pin', '位置选择', 'extra1'), ('Person', '人员选择', 'extra3'),
    ]
    mapping, files, validation = {}, {}, []
    for key, (im, hot) in assets.items():
        im.save(ROOT / 'assets' / f'{key}.png')
    for i, (role, name, key) in enumerate(roles, 1):
        relative = f'cursors/{i:02}_{name}.cur'
        path = ROOT / relative
        path.write_bytes(build_cur(*assets[key], sizes=SIZES))
        mapping[role] = relative
        files.setdefault(key, relative)
        validation.append({'file': relative, 'entries': inspect_cur(path.read_bytes()), 'windows': validate_windows(str(path), sizes=SIZES)})
    for key, name, *_ in SPECS[12:]:
        relative = f'alternatives/{name}.cur'
        path = ROOT / relative
        path.write_bytes(build_cur(*assets[key], sizes=SIZES))
        files[key] = relative
        validation.append({'file': relative, 'entries': inspect_cur(path.read_bytes()), 'windows': validate_windows(str(path), sizes=SIZES)})
    manifest = {'name': '这狗', 'version': '1.0-static-reference', 'mapping': mapping, 'sizes': SIZES,
                'notes': 'Original sheet artwork extracted; static reconstruction, not original animated files. Help/Pin/Person reuse reference designs.',
                'source_url': 'https://www.xiaohongshu.com/discovery/item/696b5835000000000e00c7a4',
                'source_author': '你自己做吧', 'artwork_provenance': origins}
    (ROOT / 'theme.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'reference' / '验证结果.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding='utf-8')
    if not all(item['windows']['valid'] for item in validation):
        raise RuntimeError('Cursor loading/hotspot validation failed; see reference/验证结果.json')
    previews(assets, mapping, files)
    demo_html(assets, mapping, files)
    print(json.dumps({'cursor_files': len(validation), 'sizes': SIZES, 'validated_with_windows': True, 'root': str(ROOT)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
