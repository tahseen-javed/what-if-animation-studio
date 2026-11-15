"""Director v0 (Phase 1): plans every chapter of a video as data for the compiler, then builds the music and sfx stems.
python tools/director.py <video>
Reads  videos/<video>/{video.json, chapters.json}, dna/<video>.json, each chapter's words.json and voice.wav.
Writes what-if-studio/out/<chapter>/plan.json (PlanFilm props), public/<chapter>/{music,sfx}.wav, videos/<video>/shotlist.json.
Rules: cuts land on word starts; an 8 s hook montage; a pattern interrupt every 12-15 s; scenes of 2-4 shots per
location; a background never returns within 20 s; consecutive shots never share framing; no shot tuple repeats in a
video; (set, angle, cam) combos are capped across the last 100 videos (docs/NOVELTY.md)."""
import math, os, random, re, sys

import numpy as np

from common import FPS, LIB, ROOT, SR, STUDIO, clip, decode, duration, load, save, vdir, write_wav
from shot_budget import budget

NEG = set("no not never can't cant lose lost danger die dead death problem worst fail scared fear dark trapped alone panic wrong".split())
MOVE = {'run': 'run', 'ran': 'run', 'chase': 'run', 'escape': 'run', 'flee': 'run', 'walk': 'walk', 'go': 'walk', 'move': 'walk',
        'jump': 'jump', 'fly': 'jump', 'fall': 'tumble', 'fell': 'tumble'}
CALM = ['point', 'present', 'lean', 'crossArms', 'think', 'nod', 'breathe', 'reach', 'wave', 'cool', 'idle']
FRIEND = ['idle', 'nod', 'crossArms', 'lean', 'think', 'breathe']
SFX_FOR = {'whip': 'fall_whoosh', 'flash': 'pop', 'glitch': 'glitch', 'shake': 'land', 'zoom': 'paste_pop', 'spin': 'dizzy', 'punch': 'drone_hit', 'card': 'title_boom'}
COLOUR = {'warm>cool>warm': ['warm', 'cool', 'warm'], 'cool>warm': ['cool', 'cool', 'warm'], 'neutral>red>neutral': ['none', 'red', 'none'],
          'desat>sat': ['desat', 'desat', 'sat'], 'sat>desat>sat': ['sat', 'desat', 'sat'], 'night>dawn': ['night', 'night', 'dawn'],
          'day>dusk>night': ['none', 'dusk', 'night'], 'steady': ['dawn', 'dawn', 'dawn']}
AMB = {'rooftop': 'roof_wind', 'apartments': 'roof_wind', 'classroom': 'class_murmur'}  # other places use the DNA's indoor bed
STOP = set('the a an and or but of to in on at for with is are was were be been it its this that you your i we they he she my our their as by from'.split())


def norm(w):
    return re.sub(r"[^\w']", '', w.lower())


def pick_pose(text, prev, rng):
    ws = [norm(w) for w in text.split()]
    pool = None
    if '?' in text:
        pool = ['think', 'shrug', 'lookAround']
    if '!' in text:
        pool = ['cheer', 'shock', 'celebrate']
    mv = [MOVE[w] for w in ws if w in MOVE]
    if mv:
        pool = mv[:1]
    elif any(w in NEG for w in ws):
        pool = ['hide', 'tremble', 'facepalm', 'shock', 'lookAround']
    elif any(re.search(r'\d', w) for w in ws):
        pool = ['point', 'present']
    pool = [p for p in (pool or CALM) if p not in prev[-2:]] or CALM
    return rng.choice(pool)


def keywords(text, n=2):
    ws = sorted({norm(w) for w in text.split() if norm(w) and norm(w) not in STOP}, key=lambda w: (-len(w), w))
    ws = [w.upper() for w in ws[:n]]
    return (ws + ['WHAT', 'NEXT?'])[:n]


def card_lines(text):
    """A title card shows the shot's own words: its fullest sentence, up to 6 words, on two lines."""
    sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    best = max(sents, key=lambda s: min(len(s.split()), 6), default='')
    ws = [w for w in (re.sub(r"[^\w'?!]", '', w).upper() for w in best.split()[:6]) if w]
    if len(ws) < 2:
        return keywords(text)
    h = (len(ws) + 1) // 2
    return [' '.join(ws[:h]), ' '.join(ws[h:])]


def option_items(text):
    """A decision's two options: 'A or B?' gives A and B, any other question gives YES and NO."""
    q = [s for s in re.split(r'(?<=[.!?])\s+', text) if '?' in s]
    q = q[-1] if q else text
    if re.search(r'\s+or\s+', q, flags=re.I):
        a, b = re.split(r'\s+or\s+', q.rstrip('?'), maxsplit=1, flags=re.I)
        return [' '.join(a.split()[-3:]).upper(), ' '.join(b.split()[:3]).upper()]
    return ['YES', 'NO']


def combo_counts(vid):
    rows = [load(p) for p in sorted((ROOT / 'registry' / 'shots').glob('*.json'))]
    rows = sorted([r for r in rows if r and r['video'] != vid], key=lambda r: r.get('created', ''))[-100:]
    c = {}
    for r in rows:
        for s in r['shots']:
            k = f"{s['set']}|{s['angle']}|{s['cam']}"
            c[k] = c.get(k, 0) + 1
    return c


def main(vid):
    meta, chs, dna = load(vdir(vid) / 'video.json'), load(vdir(vid) / 'chapters.json'), load(ROOT / 'dna' / f'{vid}.json')
    R, DM, rng, B = dna['render'], dna['dims'], random.Random(dna['seed']), budget(meta['minutes'])
    sets = [k for k, s in LIB['sets'].items() if s['cast'] and not s.get('interruptOnly')]
    angles, cams = list(LIB['angles']), LIB['cams']
    shots_per_video = sum(B['shots']) / 2
    cap = max(3, math.ceil(2 * shots_per_video * 100 / (len(sets) * len(angles) * len(cams))))
    counts = combo_counts(vid)
    durs = [duration(STUDIO / 'public' / c['slug'] / 'voice.wav') for c in chs]
    total_video = sum(durs) + 0.35 * len(durs)
    lastbg, used, prev_poses, shotlist, used_props = {}, set(), [], [], set()
    prev_angle, offset, scene = None, 0.0, None
    next_int = rng.uniform(*B['interrupt_gap_s'])
    ints = ['card', 'insert', 'punch', 'diagram']
    rng.shuffle(ints)
    n_int = 0

    def new_scene(g0, avoid):
        cand = [s for s in sets if s != avoid and g0 - lastbg.get(s, -1e9) >= B['background_gap_s']] or sorted(sets, key=lambda s: lastbg.get(s, -1e9))[:2]
        theme = dna['dims']['theme']
        seen = {r['set'] for r in shotlist}
        wts = [(2.0 if LIB['sets'][s]['theme'] == theme or theme == 'mixed' else 1.0) * (3.0 if s not in seen else 1.0) for s in cand]
        s = rng.choices(cand, weights=wts)[0]
        v = {k: rng.choice(vals) for k, vals in LIB['sets'][s]['variants'].items()}
        light = rng.choice(['night', 'moonlight']) if v.get('night') else rng.choice(R['lights'])
        friend = rng.random() < 0.45
        hm = rng.choice([0, 2]) if friend else 1
        left = 1 if g0 < B['hook_s'] else rng.randint(2, 4)  # the hook is a montage: a new place every shot
        return {'set': s, 'v': v, 'light': light, 'friend': friend, 'hm': hm, 'fm': 2 - hm, 'left': left, 'first': True}

    for ci, (ch, D) in enumerate(zip(chs, durs)):
        slug, W = ch['slug'], load(STUDIO / 'src' / 'episodes' / ch['slug'] / 'words.json', [])
        total = math.ceil((D + 0.35) * FPS)
        T = total / FPS
        cuts, t = [0.0], 0.0
        while True:
            g = offset + t
            act = min(2, int(3 * g / max(1.0, total_video)))
            L = rng.uniform(1.6, 2.2) if g < B['hook_s'] else min(6.2, max(1.8, rng.uniform(2.6, 4.4) * R['tempo'] * R['pacing'][act]))
            c = t + L
            near = [w['s'] for w in W if abs(w['s'] - c) <= 0.6 and w['s'] - t >= 1.5]
            if near:
                c = min(near, key=lambda s: abs(s - c))
            if T - c < 1.6:
                break
            cuts.append(c)
            t = c
        cuts.append(T)
        segs, infos, specs, fx = [], [], {}, []
        for k, (a, b) in enumerate(zip(cuts, cuts[1:])):
            g0, g1 = offset + a, offset + b
            af, bf = round(a * FPS), (total if k == len(cuts) - 2 else round(b * FPS))
            text = ' '.join(w['w'] + w.get('p', '') for w in W if a - 0.05 <= w['s'] < b)
            sid = f'C{ci + 1:02d}S{k + 1:03d}'
            spec = {'id': sid, 'tOff': round(offset * FPS) + af, 'seed': rng.randint(1, 9999)}
            if scene is None or scene['left'] <= 0:
                scene = new_scene(g0, scene['set'] if scene else None)
            hero = {'look': R['hero'], 'mark': scene['hm']}
            last_shot = ci == len(chs) - 1 and k == len(cuts) - 2
            if (g0 >= next_int and g0 >= B['hook_s']) or (last_shot and '?' in text):  # pattern interrupt, or the closing decision
                kind = 'options' if '?' in text else ints[n_int % len(ints)]
                n_int += kind != 'options'
                next_int = g0 + rng.uniform(*B['interrupt_gap_s'])
                spec.update(kind=kind, set=scene['set'], v=scene['v'], light=scene['light'], angle='wide', cam=rng.choice(['pushIn', 'settle', 'drift']),
                            trans=rng.choice(['flash', 'zoom', 'whip', 'dipWhite']), skin=DM['uiSkin'])
                if kind == 'options':
                    spec.update(items=option_items(text), opt=DM['optionCard'], v={**scene['v'], 'veil': 0.3})
                elif kind == 'card':
                    spec.update(text=card_lines(text), title=DM['titleLook'], v={**scene['v'], 'veil': 0.25})
                elif kind == 'insert':
                    free = [p for p in LIB['props']['insert'] if p not in used_props] or LIB['props']['insert']
                    spec.update(prop=rng.choice(free), cam=rng.choice(R['cams']))
                    used_props.add(spec['prop'])
                elif kind == 'diagram':
                    nums = re.findall(r'\d[\d,]*', text)
                    spec.update(set='schematic', text=keywords(text, 1), light='neutral')
                    if nums:
                        spec['num'] = int(nums[0].replace(',', ''))
                else:  # punch: crash into the hero's face on a flash
                    spec.update(cast=[{**hero, 'pose': 'shock'}], cam='crashZoom', trans='flash', angle='close')
                    fx.append({'f': af, 'kind': 'flash', 'o': 0.6})
                pose, angle = spec.get('cast', [{}])[0].get('pose', kind), spec['angle']
            else:
                kind = 'scene'
                for _ in range(40):
                    pool = [x for x in angles if x != prev_angle and (scene['friend'] or x not in ('twoShot', 'ots'))]
                    pref = [x for x in R['angles'] if x in pool]
                    angle = rng.choice(pref) if pref and rng.random() < 0.7 else rng.choice(pool)
                    cam = rng.choice(R['cams']) if rng.random() < 0.75 else rng.choice(cams)
                    pose = pick_pose(text, prev_poses, rng)
                    if scene['first']:
                        trans = rng.choice([x for x in R['transitions'] if x != 'cut'] or ['cut'])
                    else:
                        trans = 'cut' if rng.random() < 0.65 else rng.choice(R['transitions'])
                    free = [p for p in LIB['props']['floor'] if p not in used_props] or LIB['props']['floor']
                    prop = rng.choice(free) if rng.random() < 0.12 else ''
                    tup = '|'.join(map(str, (scene['set'], angle, scene['light'], pose, cam, prop, trans)))
                    if tup not in used and counts.get(f"{scene['set']}|{angle}|{cam}", 0) < cap:
                        break
                hx = LIB['sets'][scene['set']]
                cast = [{**hero, 'pose': pose, 'yaw': (0.35 if scene['hm'] < scene['fm'] else -0.35) if scene['friend'] else 0,
                         'facing': 1 if scene['hm'] < 2 else -1}]
                spec_ots = None
                if scene['friend'] and angle != 'ots':
                    cast.append({'look': R['friend'], 'mark': scene['fm'], 'pose': rng.choice(FRIEND), 'yaw': -cast[0]['yaw']})
                elif scene['friend']:
                    spec_ots = R['friend']
                focus = rng.choice([0, 1]) if len(cast) > 1 and angle in ('medium', 'close', 'mediumLow', 'mediumHigh', 'dutch') else 0
                spec.update(kind='scene', set=scene['set'], v=scene['v'], light=scene['light'], angle=angle, cam=cam, trans=trans, cast=cast, focus=focus)
                if prop:
                    spec['prop'] = prop
                    used_props.add(prop)
                if spec_ots:
                    spec['ots'] = spec_ots
                if not hx['cast']:
                    spec['angle'] = 'wide'
                prev_poses.append(pose)
                scene['left'] -= 1
                scene['first'] = False
            tone = COLOUR[DM['colourScript']][min(2, int(3 * g0 / max(1.0, total_video)))]  # the colour script, act by act
            if tone != 'none':
                spec['tone'] = tone
            prev_angle = spec['angle']
            if spec['kind'] != 'diagram':
                lastbg[spec['set']] = g1
            tup = '|'.join(map(str, (spec['set'], spec['angle'], spec.get('light'), pose, spec.get('cam'), spec.get('prop', ''), spec.get('trans'))))
            used.add(tup)
            specs[sid] = spec
            segs.append({'shot': sid, 'a': af, 'b': bf, 't0': 0, 't1': bf - af, 'line': text})
            infos.append({'id': sid, 'size': spec['angle'], 'key': (bf - af) // 2, 'len': bf - af, 'first': af, 'line': text})
            shotlist.append({'chapter': ci + 1, 'id': sid, 'g0': round(g0, 2), 'g1': round(g1, 2), 'kind': spec['kind'], 'set': spec['set'],
                             'angle': spec['angle'], 'cam': spec.get('cam'), 'light': spec.get('light'), 'pose': pose, 'trans': spec.get('trans'),
                             'prop': spec.get('prop', ''), 'interrupt': spec['kind'] != 'scene', 'tuple': tup, 'tone': spec.get('tone', 'none')})
        tl = {'slug': slug, 'title': vid, 'fps': FPS, 'total': total, 'segments': segs, 'shots': infos, 'fx': fx,
              'audio': {'voice': f'{slug}/voice.wav', 'music': f'{slug}/music.wav', 'sfx': f'{slug}/sfx.wav', 'voiceVol': 1, 'musicVol': 1, 'sfxVol': 1}}
        r = R
        save(STUDIO / 'out' / slug / 'plan.json', {'plan': {'id': slug, 'dna': {'grade': r['grade'], 'grain': r['grain'], 'vignette': r['vignette'], 'bg': '#0E0C1E'},
                                                           'timeline': tl, 'specs': specs}})
        ch.update(frames=total, seconds=round(T, 3), offset=round(offset, 3))
        offset += T
    save(vdir(vid) / 'chapters.json', chs)
    stems(vid, chs, shotlist, dna)
    locs = sorted({s['set'] for s in shotlist if s['kind'] in ('scene', 'punch', 'card')})
    save(vdir(vid) / 'shotlist.json', {'video': vid, 'run': os.environ.get('GITHUB_RUN_ID', 'local'), 'cap_per_100_videos': cap,
                                       'styles': {k: DM[k] for k in ('titleLook', 'uiSkin', 'optionCard', 'colourScript', 'ambience')}, 'locations': locs, 'shots': shotlist})
    print(f'{vid}: {len(shotlist)} shots over {offset:.1f}s, {len(locs)} locations, {n_int} interrupts, combo cap {cap}')


def stems(vid, chs, shotlist, dna):
    """One continuous music bed (with ambience, ducked under speech) sliced per chapter, plus a transition sfx stem."""
    total = sum(c['seconds'] for c in chs)
    n = int(total * SR) + SR
    voice_rms = np.sqrt(np.mean(decode(STUDIO / 'public' / chs[0]['slug'] / 'voice.wav') ** 2)) or 0.08
    bed = np.zeros(n)
    track = clip(dna['dims']['music'])
    if track:
        m = decode(track)
        m = np.tile(m, n // len(m) + 1)[:n]
        bed += m / (np.sqrt(np.mean(m ** 2)) + 1e-9) * voice_rms * 0.2
    house = dna['dims']['ambience'] if dna['dims']['ambience'] in ('room_tone', 'power_hum') else 'room_tone'
    level, amb = (0.06 if dna['dims']['ambience'] == 'none' else 0.12), {}
    for s in shotlist:  # ambience follows the location: wind on roofs, murmur in class, the DNA's bed indoors
        name = AMB.get(s['set'], house)
        p = clip(name)
        if not p or s['kind'] == 'diagram':
            continue
        a = amb.setdefault(name, decode(p))
        i0, i1 = int(s['g0'] * SR), min(n, int(s['g1'] * SR))
        seg = np.tile(a, (i1 - i0) // len(a) + 1)[:i1 - i0] / (np.sqrt(np.mean(a ** 2)) + 1e-9) * voice_rms * level
        f = min(len(seg) // 2, int(0.15 * SR))
        if f:
            seg[:f] *= np.linspace(0, 1, f)
            seg[-f:] *= np.linspace(1, 0, f)
        bed[i0:i1] += seg
    duck = np.ones(n)
    for c in chs:
        for w in load(STUDIO / 'src' / 'episodes' / c['slug'] / 'words.json', []):
            duck[int((c['offset'] + w['s'] - 0.15) * SR):int((c['offset'] + w['e'] + 0.15) * SR)] = 0.65
    k = int(0.25 * SR) // 2  # smooth the ducking with an O(n) moving average (a 0.25 s window)
    cs = np.concatenate([[0.0], np.cumsum(duck)])
    idx = np.arange(n)
    lo, hi = np.clip(idx - k, 0, n), np.clip(idx + k, 0, n)
    duck = (cs[hi] - cs[lo]) / np.maximum(1, hi - lo)
    fade = np.minimum(1, np.minimum(np.arange(n) / (2 * SR), (n - np.arange(n)) / (2 * SR)))
    bed *= duck * fade
    sfx = np.zeros(n)
    cache = {}
    for s in shotlist:
        name = SFX_FOR.get('punch' if s['kind'] == 'punch' else 'card' if s['kind'] == 'card' else s['trans'])
        p = clip(name) if name else None
        if not p:
            continue
        x = cache.setdefault(name, decode(p))
        i = int(s['g0'] * SR)
        seg = x[:max(0, n - i)]
        sfx[i:i + len(seg)] += seg / (np.abs(x).max() + 1e-9) * 0.3
    for c in chs:
        a, b = int(c['offset'] * SR), int((c['offset'] + c['seconds']) * SR)
        write_wav(STUDIO / 'public' / c['slug'] / 'music.wav', bed[a:b])
        write_wav(STUDIO / 'public' / c['slug'] / 'sfx.wav', sfx[a:b])


if __name__ == '__main__':
    main(sys.argv[1])
