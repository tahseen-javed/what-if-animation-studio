"""Runs INSIDE the Chatterbox environment (called by voice.py): python chatterbox_worker.py job.json
Synthesizes each script beat with Chatterbox TTS (cached per beat; locked voice settings), aligns the script words with
faster-whisper, retakes a beat whisper cannot match (same voice, seed+1, seed+2), and, when "target_wpm" is set, reaches
that pace with natural pauses only (between sentences and at commas): the voice itself is never sped up or slowed down.
Writes the wav, words_raw.json and words_raw.stats.json (matched, total, seconds, unmatched words, retakes)."""
import difflib, hashlib, json, pathlib, re, sys, time

import numpy as np
import soundfile as sf
import torch
import torchaudio

job = json.load(open(sys.argv[1], encoding='utf-8'))
O, SR = job['opts'], 44100
cache = pathlib.Path(job['cache'])
cache.mkdir(parents=True, exist_ok=True)
from chatterbox.tts import ChatterboxTTS
from faster_whisper import WhisperModel

dev = 'cuda' if torch.cuda.is_available() else 'cpu'
tts = ChatterboxTTS.from_pretrained(device=dev)
whisper = WhisperModel(O['whisper'], device='cpu', compute_type='int8')


def trim(x, pad=0.04):
    idx = np.where(np.abs(x) > 0.012)[0]
    return x if len(idx) == 0 else x[max(0, idx[0] - int(pad * SR)):idx[-1] + int(pad * SR)]


def synth(text, take=0):
    seed = O['seed'] + take
    key = hashlib.sha1(json.dumps([text, O['exaggeration'], O['cfg_weight'], O['temperature'], O['reference'], seed]).encode()).hexdigest()[:12]
    p = cache / f'{key}.wav'
    if not p.exists():
        t0 = time.time()
        torch.manual_seed(seed)
        w = tts.generate(text, audio_prompt_path=O['reference'] or None, exaggeration=O['exaggeration'], cfg_weight=O['cfg_weight'], temperature=O['temperature'])
        w = torchaudio.functional.resample(w.detach().cpu(), tts.sr, SR).squeeze(0).numpy()
        sf.write(p, trim(w), SR, subtype='PCM_16')
        print(f'  synthesized {len(text)} chars (take {take}) in {time.time() - t0:.0f}s', flush=True)
    return sf.read(p, dtype='float32')[0]


def toks(text):
    out, cur = [], None
    for ch in text:
        if re.match(r"[\w'’]", ch):
            if cur is None:
                cur = {'w': '', 'p': ''}
                out.append(cur)
            cur['w'] += ch
        else:
            cur = None
            if out and ch.strip():
                out[-1]['p'] += ch
    return out


norm = lambda s: re.sub(r"[^\w]", '', s.lower())
ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
TENS = 'x x twenty thirty forty fifty sixty seventy eighty ninety'.split()


UNITS = {w: i for i, w in enumerate(ONES)}
TENSV = {w: 10 * i for i, w in enumerate(TENS) if i >= 2}
SCALES = {'hundred': 100, 'thousand': 1000, 'million': 10 ** 6, 'billion': 10 ** 9}
isnum = lambda w: w in UNITS or w in TENSV or w in SCALES


def value(ws):
    total, cur = 0, 0
    for w in ws:
        if w in UNITS:
            cur += UNITS[w]
        elif w in TENSV:
            cur += TENSV[w]
        elif w == 'hundred':
            cur = max(1, cur) * 100
        else:
            total, cur = total + max(1, cur) * SCALES[w], 0
    return str(total + cur)


def collapse(tokens):
    """Text normalization for the comparison: a run of number words becomes one value ("two thousand five hundred" ->
    "2500"), digits stay digits ("2,500" -> "2500"). Returns the tokens and, for each, the original indices it covers."""
    out, groups, i = [], [], 0
    while i < len(tokens):
        if isnum(tokens[i]):
            j = i
            while j < len(tokens) and (isnum(tokens[j]) or (tokens[j] == 'and' and j + 1 < len(tokens) and isnum(tokens[j + 1]))):
                j += 1
            out.append(value([t for t in tokens[i:j] if t != 'and']))
            groups.append(list(range(i, j)))
            i = j
        else:
            out.append(tokens[i])
            groups.append([i])
            i += 1
    return out, groups


def align(x, text):
    """Script words of one beat matched to whisper's words: start/end times (None where not heard) and the misses."""
    S = toks(text)
    segs, _ = whisper.transcribe(torchaudio.functional.resample(torch.from_numpy(np.ascontiguousarray(x)), SR, 16000).numpy(), language='en', word_timestamps=True, beam_size=5)
    W = []
    for seg in segs:
        for wd in seg.words:
            raw = wd.word.strip()
            num = re.fullmatch(r'\$?(\d[\d,]*)(?:st|nd|rd|th)?[.,!?]*', raw)
            parts = [num.group(1).replace(',', '')] if num else re.findall(r"[\w'’]+", raw)
            for k, part in enumerate(parts):
                d = (wd.end - wd.start) / len(parts)
                W.append((norm(part), wd.start + k * d, wd.start + (k + 1) * d))
    st, en = [None] * len(S), [None] * len(S)
    A, ga = collapse([norm(t['w']) for t in S])
    Bw, gb = collapse([w[0] for w in W])
    heard = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A, Bw, autojunk=False).get_opcodes():
        if tag != 'equal' and i2 > i1:
            heard.append({'script': ' '.join(A[i1:i2]), 'heard': ' '.join(Bw[j1:j2])})  # what whisper wrote instead
        if tag == 'equal' or (tag == 'replace' and i2 - i1 == j2 - j1):  # spelling variants count (neighbours/neighbors)
            for k in range(i2 - i1):
                if tag == 'equal' or difflib.SequenceMatcher(None, A[i1 + k], Bw[j1 + k]).ratio() >= 0.75:
                    idx, s0, e0 = ga[i1 + k], W[gb[j1 + k][0]][1], W[gb[j1 + k][-1]][2]
                    for q, i in enumerate(idx):  # a matched number spreads its time over its words
                        st[i], en[i] = s0 + (e0 - s0) * q / len(idx), s0 + (e0 - s0) * (q + 1) / len(idx)
    miss = [S[i]['w'] for i in range(len(S)) if st[i] is None]
    dur = len(x) / SR
    i = 0
    while i < len(S):  # words whisper heard differently: spread between their neighbours
        if st[i] is None:
            j = i
            while j < len(S) and st[j] is None:
                j += 1
            t1 = st[j] if j < len(S) else (W[-1][2] if W else dur)
            t0 = min(en[i - 1] if i > 0 else (W[0][1] if W else 0.0), t1)
            L = [max(1, len(S[k]['w'])) for k in range(i, j)]
            acc = t0
            for k, l in zip(range(i, j), L):
                st[k], acc = acc, acc + (t1 - t0) * l / sum(L)
                en[k] = acc
            i = j
        else:
            i += 1
    return S, st, en, miss, heard


def fade(x, n=int(0.005 * SR)):
    x = np.array(x, dtype=np.float32)
    if len(x) > 2 * n:
        x[:n] *= np.linspace(0, 1, n)
        x[-n:] *= np.linspace(1, 0, n)
    return x


# ---------------------------------------------------------------- takes: retake a beat whisper cannot match
takes, retakes = [], 0
for text in job['beats']:
    best = None
    for take in range(3):
        x = synth(text, take)
        S, st, en, miss, hr = align(x, text)
        if best is None or len(miss) < len(best[4]):
            best = (x, S, st, en, miss, hr)
        if len(miss) <= 0.03 * len(S) or take == 2:
            break
        retakes += 1
    takes.append(best)

# ---------------------------------------------------------------- pace with natural pauses only
nwords = sum(len(t[1]) for t in takes)
speech = sum(len(t[0]) for t in takes) / SR
commas = sum(1 for t in takes for w in t[1][:-1] if re.search(r'[,;:—–]', w['p']))
gaps = [1.0 for _ in takes[:-1]]  # even pauses: every pause point (sentence end or comma) gets the same length
need = 60 * nwords / O['target_wpm'] - speech if O.get('target_wpm') else 0
P = max(O['beat_pause'], min(O.get('max_pause', 1.1), need / max(1e-9, len(gaps) + commas))) if need > 0 else O['beat_pause']
C = P if need > 0 else 0
print(f'  natural pace {60 * nwords / max(1e-9, speech):.0f} wpm in speech; sentence pause {P:.2f}s, comma pause {C:.2f}s', flush=True)

audio, words, off, matched, total, unmatched, heard = [], [], 0.0, 0, 0, [], []
for b, (x, S, st, en, miss, hr) in enumerate(takes):
    heard += hr
    parts, last, st, en = [], 0.0, list(st), list(en)
    for i in range(len(S) - 1):
        if C and re.search(r'[,;:—–]', S[i]['p']):
            m = (en[i] + st[i + 1]) / 2
            parts += [fade(x[int(last * SR):int(m * SR)]), np.zeros(int(C * SR), dtype=np.float32)]
            last = m
            for j in range(i + 1, len(S)):
                st[j] += C
                en[j] += C
    parts.append(fade(x[int(last * SR):]))
    x = np.concatenate(parts)
    words += [{'w': t['w'], 's': round(off + a, 3), 'e': round(off + e, 3), 'p': t['p']} for t, a, e in zip(S, st, en)]
    matched += len(S) - len(miss)
    total += len(S)
    unmatched += miss
    pause = np.zeros(int((P * gaps[b] if b < len(gaps) else 0) * SR), dtype=np.float32)
    audio += [x, pause]
    off += len(x) / SR + len(pause) / SR
y = np.concatenate(audio)
sf.write(job['out_wav'], y / max(1e-9, np.abs(y).max()) * 0.92, SR, subtype='PCM_16')
json.dump(words, open(job['out_words'], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
json.dump({'matched': matched, 'total': total, 'seconds': round(len(y) / SR, 2), 'unmatched': unmatched[:40], 'heard': heard[:20], 'retakes': retakes},
          open(job['out_words'].replace('.json', '.stats.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(f'Chatterbox voice: {len(y) / SR:.1f}s, {total} words, {matched} matched by whisper ({100 * matched // max(1, total)}%), {retakes} retakes; unmatched: {unmatched[:12]}')
