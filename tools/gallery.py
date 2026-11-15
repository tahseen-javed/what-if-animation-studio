"""Library check (runs on CI): one still per set, a contact sheet, and how different the sets LOOK, measured with image
embeddings (torchvision ResNet-18, ImageNet weights, BSD licence): cosine distance between every pair of sets.
python tools/gallery.py <set,set,...|all> <label>   -> what-if-studio/out/gallery-<label>/{sheet.jpg, distances.json}"""
import json, subprocess, sys

import numpy as np

from common import LIB, STUDIO, save

CLIP_LIMIT = 0.106  # owner calibration 2026-11-15: between the farthest 'same' pair (0.092) and the closest 'different' pair (0.120)

arg, label = sys.argv[1], sys.argv[2]
sets = [s for s in (arg.split(',') if arg != 'all' else LIB['sets']) if LIB['sets'][s]['cast']]
n, segs, infos, specs = len(sets), [], [], {}
for i, s in enumerate(sets):
    sid = f'G{i + 1:03d}'
    segs.append({'shot': sid, 'a': i, 'b': i + 1, 't0': 0, 't1': 1})
    infos.append({'id': sid, 'size': 'wide', 'key': 30, 'len': 60, 'first': i})
    specs[sid] = {'id': sid, 'kind': 'scene', 'set': s, 'angle': 'wide', 'cam': 'static', 'light': 'neutral', 'cast': []}
out = STUDIO / 'out' / f'gallery-{label}'
out.mkdir(parents=True, exist_ok=True)
save(out / 'plan.json', {'plan': {'id': label, 'dna': {}, 'timeline': {'slug': label, 'title': label, 'fps': 30, 'total': n, 'segments': segs, 'shots': infos, 'fx': [], 'audio': {}}, 'specs': specs}})
subprocess.run(['npx', 'remotion', 'render', 'src/index.ts', 'PlanBoard', f'out/gallery-{label}/board.mp4', f'--props=out/gallery-{label}/plan.json', '--log=error'], cwd=STUDIO, check=True)
cols = 4
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(out / 'board.mp4'), '-vf', f'scale=480:-1,tile={cols}x{(n + cols - 1) // cols}:padding=4', '-frames:v', '1', str(out / 'sheet.jpg')], check=True)
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(out / 'board.mp4'), '-vf', 'scale=224:224', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
imgs = np.frombuffer(raw, np.uint8).reshape(-1, 224, 224, 3)[:n] / 255.0
import torch, torchvision  # noqa: E402

m = torchvision.models.resnet18(weights='IMAGENET1K_V1').eval()
m.fc = torch.nn.Identity()
x = (torch.tensor(imgs, dtype=torch.float32).permute(0, 3, 1, 2) - torch.tensor([0.485, 0.456, 0.406])[:, None, None]) / torch.tensor([0.229, 0.224, 0.225])[:, None, None]
with torch.no_grad():
    e = torch.nn.functional.normalize(m(x), dim=1).numpy()
rd = 1 - e @ e.T  # secondary: ResNet-18 (limit 0.15 kept, reported only)
# brightness floor: mean luminance per set; the floor is 90% of the darkest hand-made (approved) set
lum = {s: round(float((imgs[i] @ np.array([0.299, 0.587, 0.114])).mean()), 3) for i, s in enumerate(sets)}
made = [s for s in LIB['sets'] if LIB['sets'][s]['cast'] and not LIB['sets'][s].get('proc') and not LIB['sets'][s].get('ext')]
floor = round(0.9 * min(lum[s] for s in made if s in lum), 3) if any(s in lum for s in made) else None
import open_clip  # noqa: E402  primary: OpenCLIP ViT-B-32 laion2b_s34b_b79k (MIT code and weights, docs/LICENSES_QA.md)
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

clip, _, prep = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
with torch.no_grad():
    ce = torch.nn.functional.normalize(clip.eval().encode_image(torch.stack([prep(Image.fromarray((im * 255).astype('uint8'))) for im in imgs])), dim=1).numpy()
d = 1 - ce @ ce.T
pairs = sorted((float(d[i, j]), float(rd[i, j]), sets[i], sets[j]) for i in range(n) for j in range(i + 1, n))
rep = {'sets': sets, 'metric': 'OpenCLIP ViT-B-32 laion2b_s34b_b79k cosine distance', 'min_distance': round(pairs[0][0], 3),
       'median_distance': round(float(np.median([p[0] for p in pairs])), 3), 'closest_pairs': [[round(a, 3), b, c] for a, _, b, c in pairs[:6]],
       'threshold': CLIP_LIMIT, 'ok': pairs[0][0] >= CLIP_LIMIT, 'failing_pairs': [[round(a, 3), b, c] for a, _, b, c in pairs if a < CLIP_LIMIT],
       'resnet18': {'min_distance': round(min(p[1] for p in pairs), 3), 'limit': 0.15, 'ok': min(p[1] for p in pairs) >= 0.15},
       'brightness': {'floor': floor, 'dark_sets': {s: v for s, v in lum.items() if floor and v < floor}, 'per_set': lum}}
if label == 'all':  # owner calibration: the 5 most similar and 5 clearly different pairs, one sheet
    cal = pairs[:5] + pairs[-5:]
    big = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', str(out / 'board.mp4'), '-vf', 'scale=480:270', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                                       capture_output=True, check=True).stdout, np.uint8).reshape(-1, 270, 480, 3)
    sheet = Image.new('RGB', (1920, 5 * 310), '#111111')
    dr, font = ImageDraw.Draw(sheet), ImageFont.load_default(size=26)
    for k, (cd, r, a, b) in enumerate(cal):
        x, y = (k // 5) * 960, (k % 5) * 310
        sheet.paste(Image.fromarray(big[sets.index(a)]), (x, y + 36))
        sheet.paste(Image.fromarray(big[sets.index(b)]), (x + 480, y + 36))
        dr.text((x + 10, y + 4), f"#{k + 1}  {a} | {b}   CLIP {cd:.3f}   ResNet {r:.3f}", fill='#F6EFE3', font=font)
    sheet.save(out / 'calibration.jpg', quality=88)
    rep['calibration_pairs'] = [{'n': k + 1, 'a': a, 'b': b, 'clip': round(cd, 3), 'resnet': round(r, 3)} for k, (cd, r, a, b) in enumerate(cal)]
save(out / 'distances.json', rep)
print(json.dumps({k: rep[k] for k in ('min_distance', 'median_distance', 'closest_pairs', 'resnet18')}), json.dumps({'floor': floor, 'dark': rep['brightness']['dark_sets']}))
