"""The Video Doctor (P-016): ONE check, ONE fix batch, ONE verify. Zero Claude tokens; prints a short summary only.
python tools/doctor.py <video>   -> videos/<video>/doctor.json, then records the shot tuples in registry/shots/<video>.json
Phase 1 covers: length, loudness/true peak, black and frozen frames, A/V sync, shot budget (count, lengths, hook,
interrupts, locations), framing and background rules, tuple repeats, voice vs script, speaking rate, music present,
DNA novelty and Jaccard vs earlier videos. Marked SKIP until Phase 3: 360p legibility, overlay overlap, character
consistency, banding/flicker, OpenCLIP perceptual diversity."""
import json, re, subprocess, sys

from common import ROOT, STUDIO, decode, duration, load, loudness, save, vdir
from longform import master
from shot_budget import budget

SKIPPED = ['legibility_360p', 'overlay_overlap', 'character_consistency', 'banding_flicker', 'perceptual_diversity_openclip']


def detect(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-vf', 'blackdetect=d=0.4:pix_th=0.08,freezedetect=n=0.002:d=3', '-an', '-f', 'null', '-'],
                       capture_output=True, text=True, errors='ignore')
    return len(re.findall(r'black_start', r.stderr)), len(re.findall(r'freeze_start', r.stderr))


def streams(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,duration', '-of', 'json', str(path)], capture_output=True, text=True)
    s = {x['codec_type']: float(x.get('duration', 0)) for x in json.loads(r.stdout or '{}').get('streams', [])}
    return s.get('video', 0), s.get('audio', 0)


def check(vid):
    meta, chs, sl, dna = load(vdir(vid) / 'video.json'), load(vdir(vid) / 'chapters.json'), load(vdir(vid) / 'shotlist.json'), load(ROOT / 'dna' / f'{vid}.json')
    B = budget(meta['minutes'])
    final = STUDIO / 'out' / vid / f'{vid}-final.mp4'
    shots = sl['shots']
    res = []

    def add(name, ok, value, limit, severity='fail'):
        res.append({'check': name, 'ok': bool(ok), 'value': value, 'limit': limit, 'severity': 'ok' if ok else severity})

    L = duration(final)
    add('length_s', abs(L - meta['minutes'] * 60) <= 0.15 * meta['minutes'] * 60, round(L, 1), f"{meta['minutes'] * 60:.0f}s +-15%", 'warn')
    i, tp = loudness(final)
    add('loudness_lufs', abs(i + 14) <= 0.5, i, '-14 +-0.5')
    add('true_peak_dbtp', tp <= -1.5, tp, '<= -1.5')
    blacks, freezes = detect(final)
    add('black_frames', blacks == 0, blacks, 0)
    add('frozen_frames', freezes == 0, freezes, 0, 'warn')
    v, a = streams(final)
    add('av_sync_s', abs(v - a) <= 0.1, round(v - a, 3), '<= 0.1')
    lens = [s['g1'] - s['g0'] for s in shots]
    Ba = budget(L / 60)  # density limits follow the real length; the length itself is checked above
    add('shot_count', Ba['shots'][0] <= len(shots) <= Ba['shots'][1], len(shots), Ba['shots'])
    add('shot_len_s', all(1.5 - 0.05 <= x <= 8.0 for x in lens), [round(min(lens), 2), round(max(lens), 2)], B['shot_len_s'])
    add('hook_shots_8s', sum(1 for s in shots if s['g0'] < B['hook_s']) >= B['hook_min_shots'], sum(1 for s in shots if s['g0'] < B['hook_s']), f">= {B['hook_min_shots']}")
    ints = [s['g0'] for s in shots if s['interrupt']]
    gaps = [b - a for a, b in zip([0.0] + ints, ints + [L])]
    add('interrupt_max_gap_s', max(gaps) <= B['interrupt_gap_s'][1] + 3, round(max(gaps), 1), f"<= {B['interrupt_gap_s'][1]}(+3 at the end)", 'warn')
    add('locations', len(sl['locations']) >= Ba['locations'][0], len(sl['locations']), Ba['locations'])
    add('consecutive_framing', all(x['angle'] != y['angle'] for x, y in zip(shots, shots[1:])), sum(x['angle'] == y['angle'] for x, y in zip(shots, shots[1:])), 0)
    last, bad, prev = {}, 0, None
    for s in shots:  # a background may continue inside its scene, but may not come back within 20 s after leaving
        if s['kind'] == 'diagram':
            continue
        if prev and s['set'] != prev['set'] and s['set'] in last and s['g0'] - last[s['set']] < B['background_gap_s']:
            bad += 1
        if prev and prev['set'] != s['set']:
            last[prev['set']] = prev['g1']
        prev = s
    add('background_return_20s', bad == 0, bad, 0)
    tups = [s['tuple'] for s in shots]
    add('tuple_repeats', len(tups) == len(set(tups)), len(tups) - len(set(tups)), 0)
    stats = [load(STUDIO / 'out' / c['slug'] / 'words_raw.stats.json', {}) for c in chs]
    matched, total = sum(s.get('matched', 0) for s in stats), sum(s.get('total', 0) for s in stats)
    add('voice_vs_script_pct', total and matched / total >= 0.95, round(100 * matched / max(1, total), 1), '>= 95')
    speech = sum(duration(STUDIO / 'public' / c['slug'] / 'voice.wav') for c in chs)
    wpm = 60 * total / max(1, speech)
    add('speaking_rate_wpm', B['wpm'][0] <= wpm <= B['wpm'][1], round(wpm), B['wpm'], 'warn')
    rms = [float((decode(STUDIO / 'public' / c['slug'] / 'music.wav') ** 2).mean() ** 0.5) for c in chs if (STUDIO / 'public' / c['slug'] / 'music.wav').exists()]
    add('music_present', bool(rms) and min(rms) > 0.002, [round(x, 4) for x in rms], '> 0.002 rms in every chapter')
    add('dna_novelty', dna['novelty']['ok'], dna['novelty'], 'P-019 s1')
    mine, worst = set(tups), 0.0
    for p in (ROOT / 'registry' / 'shots').glob('*.json'):
        r = load(p)
        if r and r['video'] != vid:
            other = {s['tuple'] for s in r['shots']}
            worst = max(worst, len(mine & other) / max(1, len(mine | other)))
    add('jaccard_vs_all', worst < B['jaccard_max'], round(worst, 3), f"< {B['jaccard_max']}")
    for name in SKIPPED:
        res.append({'check': name, 'ok': None, 'severity': 'skip', 'value': 'Phase 3', 'limit': ''})
    return res


def main(vid):
    first = check(vid)
    fixes = []
    if any(r['check'] in ('loudness_lufs', 'true_peak_dbtp') and r['ok'] is False for r in first):  # the one fix batch
        out = STUDIO / 'out' / vid
        master(out / f'{vid}-raw.mp4', out / f'{vid}-final.mp4')
        fixes.append('re-mastered loudness')
    final = check(vid) if fixes else first  # the one verify
    fails = [r for r in final if r['severity'] == 'fail']
    warns = [r for r in final if r['severity'] == 'warn']
    save(vdir(vid) / 'doctor.json', {'video': vid, 'checks': final, 'fixes': fixes, 'fails': len(fails), 'warns': len(warns)})
    sl, dna = load(vdir(vid) / 'shotlist.json'), load(ROOT / 'dna' / f'{vid}.json')
    save(ROOT / 'registry' / 'shots' / f'{vid}.json', {'video': vid, 'created': dna['created'],
                                                       'shots': [{k: s[k] for k in ('set', 'angle', 'cam', 'light', 'pose', 'trans', 'prop', 'tuple')} for s in sl['shots']]})
    passed = sum(1 for r in final if r['ok'])
    print(f"DOCTOR {vid}: {passed} pass, {len(fails)} fail, {len(warns)} warn, {len(SKIPPED)} skip; fixes: {fixes or 'none'}")
    for r in fails + warns:
        print(f"  {r['severity'].upper()} {r['check']}: {r['value']} (limit {r['limit']})")


if __name__ == '__main__':
    main(sys.argv[1])
