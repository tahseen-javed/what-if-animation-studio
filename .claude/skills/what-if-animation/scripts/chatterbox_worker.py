"""Runs INSIDE the Chatterbox environment (called by voice.py): python chatterbox_worker.py job.json
Synthesizes each script beat with Chatterbox TTS (cached per beat, fixed seed), joins them, then aligns the script
words to the audio with faster-whisper so plan.py can cue cuts on words. Writes the wav and words_raw.json."""
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


def trim(x, pad=0.04):
    idx = np.where(np.abs(x) > 0.012)[0]
    return x if len(idx) == 0 else x[max(0, idx[0] - int(pad * SR)):idx[-1] + int(pad * SR)]


def synth(text):
    key = hashlib.sha1(json.dumps([text, O['exaggeration'], O['cfg_weight'], O['temperature'], O['reference'], O['seed']]).encode()).hexdigest()[:12]
    p = cache / f'{key}.wav'
    if not p.exists():
        t0 = time.time()
        torch.manual_seed(O['seed'])
        w = tts.generate(text, audio_prompt_path=O['reference'] or None, exaggeration=O['exaggeration'], cfg_weight=O['cfg_weight'], temperature=O['temperature'])
        w = torchaudio.functional.resample(w.detach().cpu(), tts.sr, SR).squeeze(0).numpy()
        sf.write(p, trim(w), SR, subtype='PCM_16')
        print(f'  synthesized {len(text)} chars in {time.time() - t0:.0f}s', flush=True)
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
whisper = WhisperModel(O['whisper'], device='cpu', compute_type='int8')
pause = np.zeros(int(O['beat_pause'] * SR), dtype=np.float32)
audio, words, off, matched, total = [], [], 0.0, 0, 0
for text in job['beats']:
    x = synth(text)
    dur = len(x) / SR
    S = toks(text)
    segs, _ = whisper.transcribe(torchaudio.functional.resample(torch.from_numpy(x), SR, 16000).numpy(), language='en', word_timestamps=True, beam_size=5)
    W = []
    for seg in segs:
        for wd in seg.words:
            parts = re.findall(r"[\w'’]+", wd.word)
            for k, part in enumerate(parts):
                d = (wd.end - wd.start) / len(parts)
                W.append((norm(part), wd.start + k * d, wd.start + (k + 1) * d))
    n = len(S)
    st, en = [None] * n, [None] * n
    for b in difflib.SequenceMatcher(None, [norm(t['w']) for t in S], [w[0] for w in W], autojunk=False).get_matching_blocks():
        for k in range(b.size):
            st[b.a + k], en[b.a + k] = W[b.b + k][1], W[b.b + k][2]
    matched += sum(v is not None for v in st)
    total += n
    i = 0
    while i < n:  # script words whisper heard differently (numbers, abbreviations): spread between their neighbours
        if st[i] is None:
            j = i
            while j < n and st[j] is None:
                j += 1
            t1 = st[j] if j < n else (W[-1][2] if W else dur)
            t0 = min(en[i - 1] if i > 0 else (W[0][1] if W else 0.0), t1)
            L = [max(1, len(S[k]['w'])) for k in range(i, j)]
            acc = t0
            for k, l in zip(range(i, j), L):
                st[k], acc = acc, acc + (t1 - t0) * l / sum(L)
                en[k] = acc
            i = j
        else:
            i += 1
    words += [{'w': t['w'], 's': round(off + a, 3), 'e': round(off + b, 3), 'p': t['p']} for t, a, b in zip(S, st, en)]
    audio += [x, pause]
    off += dur + len(pause) / SR
y = np.concatenate(audio)
sf.write(job['out_wav'], y / max(1e-9, np.abs(y).max()) * 0.92, SR, subtype='PCM_16')
json.dump(words, open(job['out_words'], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(f'Chatterbox voice: {len(y) / SR:.1f}s, {total} words, {matched} matched by whisper ({100 * matched // max(1, total)}%)')
