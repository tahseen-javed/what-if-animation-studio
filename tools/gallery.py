"""Library check (runs on CI): one still per set, a contact sheet, and how different the sets LOOK, measured with image
embeddings (torchvision ResNet-18, ImageNet weights, BSD licence): cosine distance between every pair of sets.
python tools/gallery.py <set,set,...|all> <label>   -> what-if-studio/out/gallery-<label>/{sheet.jpg, distances.json}"""
import json, subprocess, sys

import numpy as np

from common import LIB, STUDIO, save

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
d = 1 - e @ e.T
pairs = sorted((float(d[i, j]), sets[i], sets[j]) for i in range(n) for j in range(i + 1, n))
near = {s: round(float(min(d[i, j] for j in range(n) if j != i)), 3) for i, s in enumerate(sets)}
rep = {'sets': sets, 'min_distance': round(pairs[0][0], 3), 'median_distance': round(float(np.median([p[0] for p in pairs])), 3),
       'closest_pairs': [[round(a, 3), b, c] for a, b, c in pairs[:6]], 'nearest_neighbour': near, 'threshold': 0.15, 'ok': pairs[0][0] >= 0.15}
save(out / 'distances.json', rep)
print(json.dumps({k: rep[k] for k in ('min_distance', 'median_distance', 'closest_pairs', 'ok')}))
