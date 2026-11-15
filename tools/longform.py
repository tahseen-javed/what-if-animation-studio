"""Long-form pipeline steps run by .github/workflows/long-form.yml (one chapter = one episode folder for voice.py).
python tools/longform.py prep <video> [--chapter-seconds 75]   split script.txt into chapters, sample the DNA, print the matrix
python tools/longform.py join <video>                           concat the chapter renders, master to -14 LUFS / <= -1.5 dBTP
videos/<video>/script.txt is used word for word; [bracketed tags] are hints for the director and are never spoken."""
import json, os, re, subprocess, sys

from common import FPS, ROOT, STUDIO, load, save, vdir
import dna as dnamod

VOICE = {'seed': 1234, 'exaggeration': 0.5, 'cfg_weight': 0.5, 'temperature': 0.8, 'beat_pause': 0.35, 'target_wpm': 140}
GAPS = {'word': 0.25, 'comma': 0.6, 'sentence': 1.3, 'question': 1.4}  # caps only: the worker sets the natural pauses


def prep(vid, chapter_seconds=75.0):
    d = vdir(vid)
    script = (d / 'script.txt').read_text(encoding='utf-8-sig')
    meta = load(d / 'video.json', {})
    paras = [re.sub(r'\s+', ' ', re.sub(r'\[[^\]]*\]', '', p)).strip() for p in re.split(r'\n\s*\n', script)]
    paras = [p for p in paras if p]
    words = sum(len(p.split()) for p in paras)
    meta.setdefault('minutes', round(words / 140, 2))
    meta.update(id=vid, words=words)
    save(d / 'video.json', meta)
    target = chapter_seconds * 140 / 60
    chapters, cur = [], []
    for p in paras:
        sents = [s.strip() for s in re.split(r'(?<=[.!?…])\s+', p) if s.strip()]
        for i, s in enumerate(sents):
            cur.append(s)
            n = sum(len(x.split()) for x in cur)
            if n >= 1.3 * target or (n >= target and i == len(sents) - 1):
                chapters.append(cur)
                cur = []
    if cur:
        if chapters and sum(len(x.split()) for x in cur) < 0.5 * target:
            chapters[-1] += cur
        else:
            chapters.append(cur)
    rows = []
    for i, sents in enumerate(chapters, 1):
        slug = f'{vid}-c{i:02d}'
        save(STUDIO / 'src' / 'episodes' / slug / 'episode.json', {
            'id': f'Ch{i:02d}', 'slug': slug, 'topic': meta.get('title', vid), 'title': ['', ''],
            'script': [{'beat': f'{i}.{k + 1}', 'text': s} for k, s in enumerate(sents)], 'voice': VOICE, 'gaps': GAPS})
        rows.append({'slug': slug, 'words': sum(len(s.split()) for s in sents)})
    save(d / 'chapters.json', rows)
    if not (ROOT / 'dna' / f'{vid}.json').exists():
        save(ROOT / 'dna' / f'{vid}.json', dnamod.sample(vid))
    out = json.dumps([r['slug'] for r in rows])
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'chapters={out}\n')
    print(f'{vid}: {words} words, ~{meta["minutes"]} min, {len(rows)} chapters {out}')


def master(src, dst):
    """Two-pass loudnorm to -14 LUFS (true-peak target -2 dB so the AAC file stays under -1.5 dBTP); video copied."""
    a = 'loudnorm=I=-14:TP=-2.0:LRA=11'
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(src), '-af', a + ':print_format=json', '-f', 'null', '-'], capture_output=True, text=True, errors='ignore')
    m = json.loads(r.stderr[r.stderr.rfind('{'):r.stderr.rfind('}') + 1])
    a2 = (f"{a}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-c:v', 'copy', '-af', a2, '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', str(dst)], check=True)


def join(vid):
    chs = load(vdir(vid) / 'chapters.json')
    out = STUDIO / 'out' / vid
    out.mkdir(parents=True, exist_ok=True)
    run = lambda *a: subprocess.run(['ffmpeg', '-v', 'error', '-y', *map(str, a)], check=True)
    for c in chs:  # each chapter's audio cut or padded to exactly its frame count: sample-accurate, so no drift can build up
        run('-i', STUDIO / 'out' / c['slug'] / 'chapter.mp4', '-vn', '-af', 'apad', '-t', f"{c['frames'] / FPS:.6f}", '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', out / f"{c['slug']}.wav")
    (out / 'v.txt').write_text(''.join(f"file '{(STUDIO / 'out' / c['slug'] / 'chapter.mp4').as_posix()}'\n" for c in chs), encoding='utf-8')
    (out / 'a.txt').write_text(''.join(f"file '{(out / (c['slug'] + '.wav')).as_posix()}'\n" for c in chs), encoding='utf-8')
    run('-f', 'concat', '-safe', '0', '-i', out / 'v.txt', '-c', 'copy', '-an', out / 'video.mp4')
    run('-f', 'concat', '-safe', '0', '-i', out / 'a.txt', '-c', 'copy', out / 'audio.wav')
    raw = out / f'{vid}-raw.mkv'
    run('-i', out / 'video.mp4', '-i', out / 'audio.wav', '-map', '0:v', '-map', '1:a', '-c', 'copy', raw)
    master(raw, out / f'{vid}-final.mp4')
    print(f'joined {len(chs)} chapters -> {out / f"{vid}-final.mp4"}')


if __name__ == '__main__':
    cmd, vid = sys.argv[1], sys.argv[2]
    if cmd == 'prep':
        prep(vid, float(sys.argv[sys.argv.index('--chapter-seconds') + 1]) if '--chapter-seconds' in sys.argv else 75.0)
    elif cmd == 'join':
        join(vid)
