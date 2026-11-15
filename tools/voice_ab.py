"""A/B test (runs on CI, not locked): the default voice, seed 1234, exaggeration 0.5, temperature 0.8, at cfg_weight 0.5
vs 0.3 on the same ~20 s text. Writes ab/cfg05.mp3, ab/cfg03.mp3 and ab/ab.json: words per minute of each take
(edges trimmed, no pauses added) and the speaker similarity of the two (Chatterbox's own voice encoder, cosine)."""
import json, pathlib, subprocess

import numpy as np
import torch
import torchaudio
from chatterbox.tts import ChatterboxTTS

words = open('videos/test-60s/script.txt', encoding='utf-8').read().split()
end = next(i for i in range(45, len(words)) if words[i][-1] in '.?!')
text = ' '.join(words[:end + 1])
tts = ChatterboxTTS.from_pretrained(device='cpu')
out = pathlib.Path('ab')
out.mkdir(exist_ok=True)
res, emb = {'text': text, 'words': end + 1}, {}
for name, cfg in (('cfg05', 0.5), ('cfg03', 0.3)):
    torch.manual_seed(1234)
    x = tts.generate(text, exaggeration=0.5, cfg_weight=cfg, temperature=0.8).detach().cpu().squeeze(0).numpy()
    idx = np.where(np.abs(x) > 0.012)[0]
    x = x[idx[0]:idx[-1]] if len(idx) else x
    torchaudio.save(str(out / f'{name}.wav'), torch.from_numpy(x).unsqueeze(0), tts.sr)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(out / f'{name}.wav'), '-b:a', '192k', str(out / f'{name}.mp3')], check=True)
    emb[name] = np.asarray(tts.ve.embeds_from_wavs([torchaudio.functional.resample(torch.from_numpy(x), tts.sr, 16000).numpy()], sample_rate=16000)).mean(0)
    res[name] = {'cfg_weight': cfg, 'seconds': round(len(x) / tts.sr, 2), 'wpm': round(60 * (end + 1) / (len(x) / tts.sr))}
a, b = emb['cfg05'], emb['cfg03']
res['speaker_similarity'] = round(float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b))), 4)
json.dump(res, open(out / 'ab.json', 'w'), indent=1)
print(json.dumps(res))
