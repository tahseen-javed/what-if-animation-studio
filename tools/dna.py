"""Design DNA per video (P-019 section 1): sampled from a seed, checked for novelty against every earlier video.
python tools/dna.py <video> [--seed N]   -> dna/<video>.json
Novelty (docs/NOVELTY.md): differ from each of the last 50 videos in >= 6 dimensions, and normalized Hamming distance
>= 0.4 from ALL earlier videos. Resamples until both hold (up to 2000 tries), else keeps the most distant and warns."""
import datetime, hashlib, random, sys

from common import LIB, ROOT, load, save

DIMS = {
    'palette': sorted(LIB['palettes']),
    'lighting': ['warmHome', 'nightCity', 'drama', 'soft', 'fire', 'cool', 'mixed', 'bright'],
    'camGrammar': ['calm', 'kinetic', 'documentary', 'dreamy', 'thriller', 'comic', 'epic', 'intimate'],
    'transitionSet': ['clean', 'energetic', 'smooth', 'glitchy', 'playful', 'cinematic', 'comic', 'punchy'],
    'titleLook': ['bold', 'outline', 'stacked', 'handwritten', 'neonSign', 'stamp'],
    'uiSkin': ['pill', 'glass', 'chalk', 'terminal', 'paper', 'neon'],
    'optionCard': ['tiles', 'split', 'stack', 'badge', 'ticket'],
    'music': ['music-4cdabe20', 'music-b8bb1e95'],
    'moodArc': ['rise', 'fall-rise', 'steady-tense', 'calm-burst', 'mystery-reveal', 'comic-bounce'],
    'ambience': ['room_tone', 'roof_wind', 'class_murmur', 'power_hum', 'none'],
    'pacing': ['steady', 'accelerate', 'breathe', 'punchy', 'slowburn', 'wave'],
    'intensity': ['low-high', 'high-low-high', 'steady', 'peaks', 'crescendo', 'pulse'],
    'outfit': [f'{h}+{f}' for h in LIB['outfits']['hero'] for f in LIB['outfits']['friend']],
    'theme': ['house', 'city', 'school', 'mixed'],
    'colourScript': ['warm>cool>warm', 'cool>warm', 'neutral>red>neutral', 'desat>sat', 'sat>desat>sat', 'night>dawn', 'day>dusk>night', 'steady'],
}
LIGHTING = {
    'warmHome': ['dusk', 'golden', 'candle'], 'nightCity': ['night', 'moonlight', 'neon'], 'drama': ['storm', 'noir', 'alarm', 'dusk'],
    'soft': ['dawn', 'overcast', 'golden'], 'fire': ['firelight', 'candle', 'dusk'], 'cool': ['moonlight', 'underwater', 'overcast'],
    'mixed': ['dusk', 'night', 'neon', 'golden'], 'bright': ['neutral', 'golden', 'dawn'],
}
CAMS = {
    'calm': (['static', 'drift', 'pushIn', 'pullOut', 'panLeft', 'panRight', 'settle'], 1.15, ['wide', 'medium', 'twoShot', 'mediumHigh']),
    'kinetic': (['handheld', 'whipIn', 'crashZoom', 'arc', 'pushIn', 'riseUp'], 0.85, ['medium', 'close', 'dutch', 'mediumLow']),
    'documentary': (['drift', 'pushIn', 'panLeft', 'panRight', 'tiltUp', 'static'], 1.05, ['wide', 'medium', 'ots', 'close']),
    'dreamy': (['drift', 'arc', 'pullOut', 'riseUp', 'settle'], 1.2, ['wide', 'wideLow', 'medium', 'close']),
    'thriller': (['handheld', 'dollyZoom', 'pushIn', 'tiltDown', 'crashZoom'], 0.9, ['close', 'extremeClose', 'dutch', 'ots', 'mediumLow']),
    'comic': (['whipIn', 'crashZoom', 'settle', 'pushIn', 'static'], 0.9, ['medium', 'close', 'twoShot', 'wide']),
    'epic': (['riseUp', 'arc', 'pullOut', 'tiltUp', 'dollyZoom'], 1.1, ['wide', 'wideLow', 'mediumLow', 'twoShot']),
    'intimate': (['pushIn', 'drift', 'settle', 'static'], 1.1, ['close', 'medium', 'ots', 'extremeClose']),
}
TRANS = {
    'clean': ['cut', 'cut', 'dipBlack', 'zoom'], 'energetic': ['whip', 'flash', 'shake', 'cut'], 'smooth': ['blur', 'iris', 'cut', 'slideL'],
    'glitchy': ['glitch', 'cut', 'flash', 'whip'], 'playful': ['spin', 'zoom', 'slideR', 'cut'], 'cinematic': ['dipBlack', 'cut', 'blur', 'dipWhite'],
    'comic': ['slideL', 'slideR', 'iris', 'flash'], 'punchy': ['zoom', 'shake', 'cut', 'flash'],
}
PACING = {'steady': [1, 1, 1], 'accelerate': [1.15, 1, 0.85], 'breathe': [0.9, 1.15, 0.9], 'punchy': [0.85, 0.9, 0.85], 'slowburn': [1.2, 1.05, 0.9], 'wave': [0.95, 1.1, 0.95]}
WINDOW, MIN_DIMS, MIN_DIST = 50, 6, 0.4


def history():
    rows = [load(p) for p in sorted((ROOT / 'dna').glob('*.json'))]
    return sorted([r for r in rows if r], key=lambda r: r.get('created', ''))


def diff(a, b):
    return sum(a['dims'][k] != b['dims'].get(k) for k in DIMS)


def sample(vid, seed=None):
    seed = seed if seed is not None else int(hashlib.sha1(vid.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    hist = [h for h in history() if h['video'] != vid]
    recent = hist[-WINDOW:]
    best, best_score = None, -1
    for tries in range(1, 2001):
        cand = {'dims': {k: rng.choice(v) for k, v in DIMS.items()}}
        dmin_recent = min((diff(cand, h) for h in recent), default=len(DIMS))
        dist_all = min((diff(cand, h) / len(DIMS) for h in hist), default=1.0)
        score = min(dmin_recent / MIN_DIMS, dist_all / MIN_DIST)
        if score > best_score:
            best, best_score = (cand, dmin_recent, dist_all, tries), score
        if dmin_recent >= MIN_DIMS and dist_all >= MIN_DIST:
            break
    cand, dmin_recent, dist_all, tries = best
    d = cand['dims']
    cams, tempo, bias = CAMS[d['camGrammar']]
    hero, friend = d['outfit'].split('+')
    return {
        'video': vid, 'seed': seed, 'created': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), 'dims': d,
        'render': {
            'grade': LIB['palettes'][d['palette']], 'lights': LIGHTING[d['lighting']], 'cams': cams, 'tempo': tempo, 'angles': bias,
            'transitions': TRANS[d['transitionSet']], 'pacing': PACING[d['pacing']], 'hero': hero, 'friend': friend,
            'grain': d['palette'] not in ('pastel', 'sunbleached'), 'vignette': True,
        },
        'novelty': {'min_dims_diff_last50': dmin_recent, 'min_dist_all': round(dist_all, 3), 'tries': tries,
                    'ok': dmin_recent >= MIN_DIMS and dist_all >= MIN_DIST, 'compared': len(hist)},
    }


if __name__ == '__main__':
    vid = sys.argv[1]
    seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else None
    dna = sample(vid, seed)
    save(ROOT / 'dna' / f'{vid}.json', dna)
    print(f"DNA {vid}: {dna['dims']['palette']}/{dna['dims']['lighting']}/{dna['dims']['camGrammar']}/{dna['dims']['transitionSet']} "
          f"novelty {'OK' if dna['novelty']['ok'] else 'WARN'} {dna['novelty']}")
