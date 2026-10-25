"""Hand-edited, pure-vector alternative of the supplied normal cursor.

All output is confined to the adjacent editable directory.  This optional
redrawing does not modify the source extraction or the installable theme.
Requires only the already bundled Node.js sharp package for PNG export.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "editable"
OUT.mkdir(exist_ok=True)
SVG = r'''<svg xmlns="http://www.w3.org/2000/svg" width="229" height="229" viewBox="0 0 229 229">
  <title>这狗 — 正常选择光标，手工矢量重绘备选</title>
  <desc>229 by 229 transparent canvas. All features are editable vector paths and gradients. Manually reconstructed from the supplied display image; not an original source drawing.</desc>
  <metadata>source=../assets/normal.png; hotspot=14,22; optional=true; bitmap-elements=0</metadata>
  <defs>
    <radialGradient id="blush-left-gradient" cx="50%" cy="48%" r="50%">
      <stop offset="0" stop-color="#efd4cf" stop-opacity=".85"/>
      <stop offset=".55" stop-color="#efd4cf" stop-opacity=".52"/>
      <stop offset="1" stop-color="#efd4cf" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="blush-right-gradient" cx="50%" cy="48%" r="50%">
      <stop offset="0" stop-color="#edcdc7" stop-opacity=".88"/>
      <stop offset=".58" stop-color="#efd4cf" stop-opacity=".54"/>
      <stop offset="1" stop-color="#efd4cf" stop-opacity="0"/>
    </radialGradient>
    <path id="character-silhouette" d="M98.1 76.0 C115.5 73.0 132.5 70.6 143.1 70.2 C140.2 63.4 142.7 57.1 147.9 55.8 C151.8 54.5 155.3 57.2 158.2 59.3 C154.7 55.1 156.4 52.7 161.1 51.4 C172.4 48.5 186.9 58.5 196.2 68.8 C202.0 75.4 204.3 82.0 201.5 86.9 C200.1 89.0 195.2 90.0 193.1 91.0 C204.9 107.3 213.1 129.9 213.1 150.8 C214.0 169.1 202.0 176.6 186.5 180.7 L169.9 184.0 C171.1 189.5 172.7 196.0 170.2 200.7 C168.6 203.6 166.1 204.4 163.7 202.8 L162.8 204.3 L161.3 202.7 C158.3 207.4 154.2 213.1 152.1 214.4 C149.6 215.4 148.2 213.0 148.1 209.5 L137.1 210.0 C138.7 215.0 133.8 217.5 129.9 215.0 C126.5 213.1 125.1 210.0 123.9 208.1 C123.4 211.5 122.2 213.1 120.8 211.4 L119.2 212.4 L117.7 210.7 L116.0 211.7 C111.2 208.5 112.0 202.3 112.8 193.5 C105.9 194.0 97.0 195.0 88.3 194.1 C70.6 194.0 61.0 182.1 59.9 168.6 C57.2 149.9 59.7 130.6 66.2 112.8 C61.1 116.1 55.2 114.8 53.0 110.2 C49.3 102.3 58.0 86.4 67.7 74.5 C76.1 64.6 81.4 61.9 85.2 65.2 C85.3 61.9 91.0 59.7 95.3 63.5 C101.1 66.4 99.8 71.1 98.1 76.0 Z"/>
    <clipPath id="clip-character"><use href="#character-silhouette"/></clipPath>
    <path id="left-eye-shape" d="M72.0 119.3 C81.5 107.1 96.2 106.3 108.3 117.8 C119.4 128.3 123.9 144.3 119.0 156.6 C113.8 169.5 96.5 174.4 79.0 170.7 C64.7 167.8 60.1 156.5 61.7 143.3 C62.6 134.5 66.6 125.5 72.0 119.3 Z"/>
    <path id="left-pupil-shape" d="M74.2 117.5 C83.6 108.2 96.4 107.5 107.9 117.9 C118.3 127.5 123.7 144.3 118.8 156.4 C114.0 168.5 98.1 173.1 83.8 170.6 C74.0 161.9 69.2 149.0 69.7 136.2 C69.8 129.7 71.1 123.0 74.2 117.5 Z"/>
    <clipPath id="clip-left-pupil"><use href="#left-pupil-shape"/></clipPath>
    <path id="right-eye-shape" d="M154.5 112.6 C163.2 98.6 179.3 93.9 191.0 99.0 C201.8 103.7 206.2 120.2 206.5 133.0 C207.0 146.7 202.8 153.5 192.3 155.9 C181.8 158.6 167.6 156.9 160.2 151.8 C150.0 144.9 145.8 126.3 154.5 112.6 Z"/>
    <path id="right-pupil-shape" d="M154.6 112.5 C162.4 99.9 175.5 95.2 184.4 97.6 C193.6 103.6 197.0 118.2 197.0 132.0 C196.7 141.4 194.0 149.8 190.0 155.2 C178.7 157.0 166.9 155.9 160.0 151.1 C149.6 143.8 146.0 126.5 154.6 112.5 Z"/>
    <clipPath id="clip-right-pupil"><use href="#right-pupil-shape"/></clipPath>
  </defs>
  <g id="arrow" aria-label="三角箭头" stroke-linejoin="round" transform="translate(-1 -2.7) scale(1 1.04)">
    <path id="arrow-rim" d="M20.4 20.6 L52.8 29.2 C59.0 30.8 60.8 36.0 56.2 40.8 L32.1 64.5 C27.4 69.1 22.7 67.7 20.9 61.4 L11.0 30.0 C8.7 23.1 13.1 18.7 20.4 20.6 Z" fill="#d5e5e2" stroke="#c8dbd7" stroke-width="1.1"/>
    <path id="arrow-fill" d="M20.4 20.6 L52.8 29.2 C59.0 30.8 60.8 36.0 56.2 40.8 L32.1 64.5 C27.4 69.1 22.7 67.7 20.9 61.4 L11.0 30.0 C8.7 23.1 13.1 18.7 20.4 20.6 Z" fill="#f5faf9" stroke="#3d4b48" stroke-width="2.2"/>
  </g>
  <g id="character" aria-label="大眼白狗">
    <g id="body-and-ears" fill="#f5faf9" stroke-linecap="round" stroke-linejoin="round">
      <use id="outer-light-rim" href="#character-silhouette" stroke="#bad7d0" stroke-width="2.35"/>
      <use id="body-fill" href="#character-silhouette" stroke="#35433f" stroke-width="1.45"/>
      <path id="left-ear-fold" d="M85.2 65.2 L82.4 70.5" fill="none" stroke="#485451" stroke-width="1.0"/>
      <path id="left-paw-fold" d="M123.9 208.1 L123.0 206.0" fill="none" stroke="#485451" stroke-width="1.0"/>
    </g>
    <g id="blush" aria-label="腮红" clip-path="url(#clip-character)">
      <path id="left-cheek" d="M56 160 C65 156 91 163 106 177 C118 188 100 198 82 195 C63 193 49 180 56 160 Z" fill="url(#blush-left-gradient)"/>
      <path id="right-cheek" d="M178 148 C190 141 213 141 220 154 C227 171 206 185 190 180 C176 176 169 158 178 148 Z" fill="url(#blush-right-gradient)"/>
    </g>
    <g id="eyes" aria-label="大眼睛" stroke-linejoin="round">
      <g id="eye-left" aria-label="左眼">
        <use id="left-sclera" href="#left-eye-shape" fill="#f8fcfb" stroke="#3d4744" stroke-width="1.1"/>
        <use id="left-pupil" href="#left-pupil-shape" fill="#222b29"/>
        <g id="left-reflections" clip-path="url(#clip-left-pupil)">
          <path id="left-reflection-lower" d="M76.5 163.0 C84.8 154.1 102.7 147.2 119.5 152.7 L121.5 173.5 L83.4 174.1 Z" fill="#606663"/>
          <path id="left-highlight-top" d="M76.0 111.9 C87.6 104.8 102.2 109.8 111.5 119.8 C107.2 127.7 101.9 132.0 93.4 131.4 C84.6 130.9 79.5 123.7 76.0 111.9 Z" fill="#f7fcfa"/>
          <path id="left-highlight-center-left" d="M75.6 143.9 C76.4 138.4 82.9 134.9 89.5 137.0 C95.0 138.8 97.8 144.8 94.6 149.3 C91.9 153.0 81.7 154.7 77.7 150.9 C76.0 149.6 75.0 146.7 75.6 143.9 Z" fill="#f7fcfa"/>
          <path id="left-highlight-center-right" d="M99.4 139.9 C100.7 135.9 108.0 133.2 112.9 136.7 C116.3 139.2 117.1 143.2 113.2 145.1 C109.3 147.0 103.1 146.0 100.7 143.9 C99.3 142.8 98.9 141.5 99.4 139.9 Z" fill="#f7fcfa"/>
        </g>
      </g>
      <g id="eye-right" aria-label="右眼">
        <use id="right-sclera" href="#right-eye-shape" fill="#f8fcfb" stroke="#3d4744" stroke-width="1.1"/>
        <use id="right-pupil" href="#right-pupil-shape" fill="#222b29"/>
        <g id="right-reflections" clip-path="url(#clip-right-pupil)">
          <path id="right-reflection-lower" d="M156.9 149.0 C166.1 138.2 182.7 133.7 197.6 138.3 L199.8 161.5 L160.1 158.8 Z" fill="#606663"/>
          <path id="right-highlight-top" d="M153.5 104.5 C163.1 97.8 174.4 96.8 183.2 98.9 C184.1 107.9 178.6 116.5 171.0 119.5 C164.6 122.2 157.4 118.9 154.1 114.8 C152.7 112.5 152.6 108.6 153.5 104.5 Z" fill="#f7fcfa"/>
          <path id="right-highlight-center-left" d="M155.7 131.9 C155.3 125.4 161.0 123.0 165.9 125.1 C170.6 127.0 172.7 131.5 170.1 135.4 C167.7 139.1 160.6 140.3 157.4 137.5 C156.1 136.2 155.7 134.2 155.7 131.9 Z" fill="#f7fcfa"/>
          <path id="right-highlight-center-right" d="M173.7 123.9 C174.8 118.7 179.8 114.2 184.8 114.6 C190.6 114.6 193.1 119.3 191.4 123.6 C189.6 128.0 182.5 133.0 177.7 133.3 C173.9 133.3 172.4 129.9 173.7 123.9 Z" fill="#f7fcfa"/>
        </g>
      </g>
    </g>
    <g id="face" aria-label="鼻子与嘴巴">
      <path id="nose" d="M126.2 149.8 C130.7 148.5 141.7 146.4 145.8 147.2 C149.7 148.1 145.4 151.6 141.4 153.8 C136.2 157.1 129.6 154.5 126.2 152.2 C125.3 151.4 125.0 150.4 126.2 149.8 Z" fill="#222b29"/>
      <path id="smile" d="M129.1 168.1 C129.5 178.1 132.3 182.3 137.6 181.9 C143.1 181.6 146.5 177.0 145.0 166.8" fill="none" stroke="#505a56" stroke-width="1.35" stroke-linecap="round"/>
    </g>
  </g>
</svg>
'''

svg_path = OUT / "normal_redrawn.svg"
svg_path.write_text(SVG, encoding="utf-8")
node = Path(r"C:\Users\30926\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe")
sharp = Path(r"C:\Users\30926\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\sharp")
js = """const sharp=require(process.argv[1]);
sharp(process.argv[2],{density:384}).resize(229,229).png().toFile(process.argv[3]);
"""
subprocess.run([str(node), "-e", js, str(sharp), str(svg_path), str(OUT / "normal_redrawn.png")], check=True)
print(svg_path)
print(OUT / "normal_redrawn.png")
