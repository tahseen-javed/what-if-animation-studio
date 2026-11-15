import React from 'react';
import {
  basePose, poseAt, faceAt, walkPose, Hero, LOOKS, Pose, Expr, CastName, camT, clamp, easeOut, easeInOut, backOut, rnd,
  Foreground, FocusRings, Tabletop, CountUp, Arrow, FONT, Mug, Phone, OpenBook, PaperBall, PizzaSlice,
  AlarmClock, Paper, GamePad, CookieStack, BookTower, CookieTop, PlateTop, Guitar, Amp,
} from '../engine';
import LIB from './library.json';
import { SETS, Mark, V } from './sets';

// The compiler: one generic shot drawn from a data spec (set, angle, light, cast pose/expression, camera move, prop,
// transition). Every video is data; no per-video code. Pure function of the shot clock t, like every engine shot.
type Layer = { fill: string; o: number; blend?: string; grad?: string; flicker?: number; pulse?: number; sat?: number; flash?: number };
type PoseDef = { p?: Partial<Pose>; expr?: Expr; loop?: string };
export type Library = {
  sets: Record<string, { theme: string; cast: boolean; interruptOnly?: boolean; variants: Record<string, (number | boolean | string)[]> }>;
  angles: Record<string, { z: number; dy?: number; rot?: number }>;
  cams: string[]; transitions: string[]; lights: Record<string, Layer[]>; poses: Record<string, PoseDef>;
  props: { floor: string[]; insert: string[] }; palettes: Record<string, string>; outfits: Record<string, string[]>;
};
export const LIBRARY = LIB as unknown as Library;

export type CastSpec = { look?: string; pose?: string; expr?: string; mark?: number; yaw?: number; facing?: 1 | -1 };
export type Spec = {
  id: string; kind?: 'scene' | 'insert' | 'card' | 'diagram' | 'punch' | 'options'; set: string; v?: V; angle?: string; cam?: string;
  light?: string; trans?: string; cast?: CastSpec[]; focus?: number; prop?: string; text?: string[]; num?: number; tOff?: number;
  seed?: number; ots?: string; edge?: number; title?: string; skin?: string; opt?: string; tone?: string; items?: string[];
};

const LIMBS = ['armL', 'armR', 'legL', 'legR'] as const;
const overshoot = (b: Pose, p: Partial<Pose>, k: number): Partial<Pose> => {
  const o: Partial<Pose> = { ...p };
  for (const key of LIMBS) {
    const q = p[key];
    if (q) o[key] = { a: b[key].a + (q.a - b[key].a) * k, b: b[key].b + (q.b - b[key].b) * k };
  }
  return o;
};

const loop = (name: string | undefined, t: number, p: Pose, seed: number): Pose => {
  const s = Math.sin;
  switch (name) {
    case 'wave': return { ...p, armR: { a: p.armR.a, b: -25 + 28 * s(t / 3.2) } };
    case 'nod': return { ...p, headTilt: p.headTilt + 5 * s(t / 4.5) };
    case 'bounce': return { ...p, y: p.y - Math.abs(s(t / 4)) * 7 * p.scale };
    case 'tremble': return { ...p, x: p.x + s(t * 2.9) * 2.2 * p.scale };
    case 'lookAround': return { ...p, yaw: 0.45 * s(t / 22 + seed), look: s(t / 15) };
    case 'sway': return { ...p, headTilt: p.headTilt + 6 * s(t / 9), tilt: p.tilt + 2.5 * s(t / 11) };
    case 'spin': return { ...p, spin: (t * 9) % 360 };
    case 'jump': {
      const c = (t % 26) / 26;
      const h = Math.sin(Math.PI * clamp((c - 0.25) / 0.6));
      return { ...p, y: p.y - h * 90 * p.scale, squash: c < 0.22 ? 0.12 : c > 0.86 ? 0.1 : -0.08 };
    }
    default: return { ...p, y: p.y + Math.sin(t / 18 + seed) * 1.5 * p.scale }; // breathing
  }
};

/** A character acting a named pose: anticipation from rest, overshoot, settle, then its loop; blinks on its own. */
const act = (c: CastSpec, m: Mark, t: number, len: number, seed: number): Pose => {
  const d = LIBRARY.poses[c.pose ?? 'idle'] ?? {};
  const expr = (c.expr ?? d.expr ?? 'neutral') as Expr;
  const facing = c.facing ?? 1;
  if (d.loop === 'walk' || d.loop === 'run') {
    const run = d.loop === 'run';
    const x = m.x + facing * (run ? 7 : 3.2) * (t - len / 2);
    return walkPose(x, t * (run ? 0.95 : 0.6), m.y, m.scale, { expr, tilt: run ? 9 : 0, yaw: facing * 0.85 }, facing);
  }
  const base: Pose = { ...basePose, x: m.x, y: m.y, scale: m.scale, yaw: c.yaw ?? 0, facing, expr };
  const target = d.p ?? {};
  let p = poseAt(t, [{ f: 0, p: {} }, { f: 7, p: overshoot(base, target, 1.12), ease: easeOut }, { f: 11, p: target }], base);
  p = loop(d.loop, t, p, seed);
  const blink = (t + seed * 37) % 96 < 3 ? 1 : p.blink;
  return { ...p, ...faceAt(t, [[0, expr]]), blink };
};

/** Framing from the angle and the subject's mark, kept inside the 1920 x 1080 world. */
const frameFor = (angle: string, m: Mark | undefined, m2: Mark | undefined) => {
  const A = LIBRARY.angles[angle] ?? LIBRARY.angles.wide;
  if (!m || angle.startsWith('wide')) return { cx: 960, cy: 540 + (A.dy ?? 0) * 0.5, z: A.z, rot: A.rot ?? 0 };
  if (angle === 'twoShot' && m2) return { cx: (m.x + m2.x) / 2, cy: m.y - 70 * m.scale, z: A.z, rot: 0 };
  const z = Math.min(5.5, Math.max(1, A.z / m.scale));
  const cy = A.z >= 3 ? m.y - 176 * m.scale : m.y - 70 * m.scale;
  return { cx: m.x, cy: cy + (A.dy ?? 0) / z, z, rot: A.rot ?? 0 };
};

const move = (name: string, t: number, len: number, f: { cx: number; cy: number; z: number; rot: number }, seed: number) => {
  const p = easeInOut(clamp(t / Math.max(1, len)));
  let { cx, cy, z, rot } = f;
  const u = 1 / z;
  switch (name) {
    case 'pushIn': z *= 1 + 0.12 * p; break;
    case 'pullOut': z *= 1.12 - 0.12 * p; break;
    case 'dollyZoom': z *= 1 + 0.2 * p; cy -= 20 * u * p; break;
    case 'panLeft': cx += (1 - 2 * p) * 70 * u; break;
    case 'panRight': cx -= (1 - 2 * p) * 70 * u; break;
    case 'tiltUp': cy += (1 - 2 * p) * 45 * u; break;
    case 'tiltDown': cy -= (1 - 2 * p) * 45 * u; break;
    case 'drift': cx += Math.sin(t / 40 + seed) * 18 * u; cy += Math.cos(t / 53 + seed) * 10 * u; break;
    case 'handheld':
      cx += (Math.sin(t * 0.37 + seed) + Math.sin(t * 0.83)) * 4 * u;
      cy += (Math.cos(t * 0.41) + Math.sin(t * 0.71 + seed)) * 3 * u;
      rot += Math.sin(t * 0.29) * 0.4;
      break;
    case 'crashZoom': z *= 0.8 + 0.2 * backOut(clamp(t / 8)); break;
    case 'whipIn': cx += (1 - easeOut(clamp(t / 7))) * 500 * u; break;
    case 'arc': cx += (1 - 2 * p) * 90 * u; rot += (1 - 2 * p) * 2; z *= 1 + 0.05 * p; break;
    case 'riseUp': cy += (1 - p) * 80 * u; z *= 1 + 0.06 * p; break;
    case 'settle': z *= 1 + 0.08 * (1 - easeOut(clamp(t / 14))); break;
    default: break;
  }
  if (rot) z *= 1.07; // cover the corners a rotation would show
  const hw = 960 / z;
  const hh = 540 / z;
  return { cx: Math.min(1920 - hw, Math.max(hw, cx)), cy: Math.min(1080 - hh, Math.max(hh, cy)), z, rot };
};

const PROPS: Record<string, (x: number, y: number, t: number, s: number) => React.ReactNode> = {
  Mug: (x, y, t, s) => <Mug x={x} y={y} rot={0} steam={1} f={t} />,
  BookTower: (x, y, t, s) => <BookTower x={x} y={y} n={6} s={s} />,
  GamePad: (x, y, t, s) => <GamePad x={x} y={y} s={s} />,
  AlarmClock: (x, y, t, s) => <AlarmClock x={x} y={y} s={s} text="03:00" on={1} />,
  CookieStack: (x, y, t, s) => <CookieStack x={x} y={y} n={5} s={s} />,
  Guitar: (x, y, t, s) => <Guitar x={x} y={y} s={s} />,
  Amp: (x, y, t, s) => <Amp x={x} y={y} s={s} led={1} />,
  Paper: (x, y) => <Paper x={x} y={y} w={300} done grade="A+" />,
  Phone: (x, y, t) => <Phone x={x} y={y} w={150} on={1} caller="UNKNOWN" buzz={1} f={t} />,
  PizzaSlice: (x, y) => <PizzaSlice x={x} y={y} len={230} drip={1} />,
  CookieTop: (x, y) => <CookieTop x={x} y={y} r={110} />,
  PlateTop: (x, y) => <PlateTop x={x} y={y} r={170} />,
  PaperBall: (x, y) => <PaperBall x={x} y={y} r={60} />,
  OpenBook: (x, y, t) => <OpenBook x={x} y={y} w={420} turn={clamp((t % 50) / 25)} />,
};

/** Light preset: screen-space layers (gradients, blend modes, flicker, pulse, storm flashes). */
const Light: React.FC<{ name?: string; t: number; uid: string }> = ({ name, t, uid }) => {
  const L = LIBRARY.lights[name ?? 'neutral'] ?? [];
  return (
    <g>
      {L.map((l, i) => {
        const id = `cl${uid}${i}`;
        let o = l.o;
        if (l.flicker) o *= 1 - l.flicker * (0.5 + 0.5 * Math.sin(t * 1.7 + i) * Math.sin(t * 0.73));
        if (l.pulse) o *= 0.55 + 0.45 * Math.sin((t / l.pulse) * Math.PI * 2);
        if (l.flash) o = t % l.flash < 2 ? 0.55 : t % l.flash < 4 ? 0.2 : 0;
        const g = l.grad && l.grad !== 'none' ? l.grad : null;
        const lin = g === 'top' || g === 'bottom' || g === 'left' || g === 'right';
        const startOn = g === 'top' || g === 'left';
        return (
          <g key={i}>
            {g ? (
              <defs>
                {lin ? (
                  <linearGradient id={id} x1="0" y1="0" x2={g === 'left' || g === 'right' ? 1 : 0} y2={g === 'top' || g === 'bottom' ? 1 : 0}>
                    <stop offset="0%" stopColor={l.fill} stopOpacity={startOn ? 1 : 0} />
                    <stop offset="100%" stopColor={l.fill} stopOpacity={startOn ? 0 : 1} />
                  </linearGradient>
                ) : (
                  <radialGradient id={id} cx="50%" cy="48%" r="72%">
                    <stop offset={g === 'edge' ? '45%' : '0%'} stopColor={l.fill} stopOpacity={g === 'edge' ? 0 : 1} />
                    <stop offset="100%" stopColor={l.fill} stopOpacity={g === 'edge' ? 1 : 0} />
                  </radialGradient>
                )}
              </defs>
            ) : null}
            <rect width={1920} height={1080} fill={g ? `url(#${id})` : l.fill} opacity={o} style={{ mixBlendMode: (l.blend ?? 'normal') as React.CSSProperties['mixBlendMode'] }} />
          </g>
        );
      })}
    </g>
  );
};

/** Entry transition, drawn in the first frames of the incoming shot (the engine cuts; the shot carries its own entry). */
const entry = (name: string | undefined, t: number) => {
  const k = (n: number) => clamp(t / n);
  switch (name) {
    case 'whip': return { tr: `translate(${(1 - easeOut(k(7))) * -420} 0)`, whip: t < 6 };
    case 'zoom': { const s = 1 + 0.25 * (1 - easeOut(k(9))); return { tr: `translate(960 540) scale(${s}) translate(-960 -540)` }; }
    case 'slideL': return { tr: `translate(${(1 - easeOut(k(9))) * 560} 0)` };
    case 'slideR': return { tr: `translate(${(1 - easeOut(k(9))) * -560} 0)` };
    case 'spin': { const q = 1 - easeOut(k(10)); return { tr: `rotate(${q * 9} 960 540) translate(960 540) scale(${1 + q * 0.2}) translate(-960 -540)` }; }
    case 'shake': { const a = 16 * (1 - k(9)); return { tr: `translate(${Math.sin(t * 2.9) * a} ${Math.cos(t * 3.7) * a * 0.7})` }; }
    case 'glitch': return { tr: t < 5 ? `translate(${(rnd(7, t) - 0.5) * 60} 0)` : undefined, glitch: t < 5 };
    default: return {};
  }
};

const Overlay: React.FC<{ name?: string; t: number; uid: string }> = ({ name, t, uid }) => {
  const k = (n: number) => clamp(t / n);
  if (name === 'flash') return t < 2 ? <rect width={1920} height={1080} fill="#FFFFFF" opacity={t < 1 ? 0.9 : 0.35} /> : null;
  if (name === 'dipBlack' || name === 'dipWhite') return t < 8 ? <rect width={1920} height={1080} fill={name === 'dipBlack' ? '#000' : '#FFF'} opacity={1 - easeOut(k(8))} /> : null;
  if (name === 'glitch' && t < 5)
    return (
      <g opacity={0.55}>
        {[0, 1, 2, 3].map((i) => <rect key={i} x={0} y={rnd(t + i, 3) * 1080} width={1920} height={20 + rnd(i, t) * 60} fill={i % 2 ? '#FF2E88' : '#2EE6FF'} style={{ mixBlendMode: 'screen' }} />)}
      </g>
    );
  return null;
};

// DNA-driven UI: uiSkin colours panels and option cards, titleLook styles cards, optionCard lays out a decision.
const SKIN: Record<string, { bg: string; o: number; fg: string; acc: string; font: string; r: number }> = {
  pill: { bg: '#14121F', o: 0.78, fg: '#F6EFE3', acc: '#FFB347', font: FONT.ui, r: 40 },
  glass: { bg: '#FFFFFF', o: 0.16, fg: '#FFFFFF', acc: '#9FE7FF', font: FONT.ui, r: 26 },
  chalk: { bg: '#1F3A2E', o: 0.94, fg: '#EDEDE0', acc: '#F7D774', font: FONT.hand, r: 8 },
  terminal: { bg: '#050A05', o: 0.92, fg: '#39FF7A', acc: '#B6FFCB', font: FONT.ui, r: 4 },
  paper: { bg: '#F3E7CF', o: 0.96, fg: '#2A2118', acc: '#C2410C', font: FONT.hand, r: 10 },
  neon: { bg: '#0B0620', o: 0.86, fg: '#FF5FD2', acc: '#2FE0FF', font: FONT.title, r: 30 },
};

const Panel: React.FC<{ t: number; text: string; skin?: string }> = ({ t, text, skin }) => {
  const S = SKIN[skin ?? 'pill'] ?? SKIN.pill;
  const w = Math.max(420, text.length * 46 + 120);
  return (
    <g transform={`translate(960 300) scale(${backOut(clamp(t / 10))}) translate(-960 -300)`}>
      <rect x={960 - w / 2} y={230} width={w} height={140} rx={S.r} fill={S.bg} opacity={S.o} stroke={S.acc} strokeWidth={skin === 'neon' || skin === 'glass' ? 3 : 0} />
      <text x={960} y={325} textAnchor="middle" fontFamily={S.font} fontSize={72} fill={S.fg}>{text}</text>
    </g>
  );
};

const Card: React.FC<{ t: number; lines: string[]; style?: string }> = ({ t, lines, style }) => {
  const [a = '', b = ''] = lines;
  const p = easeOut(clamp(t / 8));
  const T = (y: number, s: string, size: number, fill: string, extra: React.SVGProps<SVGTextElement> = {}) => (
    <text x={960} y={y} textAnchor="middle" fontFamily={FONT.title} fontSize={size} fill={fill} {...extra}>{s}</text>
  );
  switch (style) {
    case 'outline':
      return <g opacity={p}>{T(500, a, 118, 'none', { stroke: '#F6EFE3', strokeWidth: 4 })}{T(640, b, 132, 'none', { stroke: '#FFB347', strokeWidth: 5 })}</g>;
    case 'stacked':
      return <g opacity={p}><rect x={960 - 420 * p} y={540} width={840 * p} height={10} fill="#FFB347" />{T(510, a, 64, '#F6EFE3', { letterSpacing: 12 })}{T(690, b, 150, '#F6EFE3')}</g>;
    case 'handwritten':
      return (
        <g opacity={p} transform="rotate(-3 960 560)">
          {T(520, a, 110, '#F6EFE3', { fontFamily: FONT.hand })}{T(650, b, 120, '#FFD27A', { fontFamily: FONT.hand })}
          <path d="M 620 690 Q 960 720 1300 680" stroke="#FFD27A" strokeWidth={8} fill="none" strokeLinecap="round" strokeDasharray={760} strokeDashoffset={760 * (1 - clamp((t - 6) / 10))} />
        </g>
      );
    case 'neonSign':
      return (
        <g opacity={p * (t % 37 < 2 ? 0.4 : 1)}>
          <filter id="cneon"><feGaussianBlur stdDeviation="8" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          <g filter="url(#cneon)">{T(500, a, 112, 'none', { stroke: '#FF5FD2', strokeWidth: 5 })}{T(640, b, 124, 'none', { stroke: '#2FE0FF', strokeWidth: 5 })}</g>
        </g>
      );
    case 'stamp': {
      const s = 1 + 0.4 * (1 - backOut(clamp(t / 7)));
      return (
        <g transform={`rotate(-8 960 560) translate(960 560) scale(${s}) translate(-960 -560)`} opacity={clamp(t / 3)}>
          <rect x={520} y={400} width={880} height={300} rx={18} fill="none" stroke="#E5383B" strokeWidth={14} />{T(520, a, 92, '#E5383B')}{T(650, b, 110, '#E5383B')}
        </g>
      );
    }
    default:
      return (
        <g opacity={p} transform={`translate(960 560) scale(${0.9 + 0.1 * p}) translate(-960 -560)`}>
          {T(506, a, 104, '#F6EFE3', { stroke: '#0E0C1E', strokeWidth: 10, paintOrder: 'stroke' })}{T(646, b, 128, '#FFB347', { stroke: '#0E0C1E', strokeWidth: 12, paintOrder: 'stroke' })}
        </g>
      );
  }
};

const Options: React.FC<{ t: number; items: string[]; style?: string; skin?: string }> = ({ t, items, style, skin }) => {
  const S = SKIN[skin ?? 'pill'] ?? SKIN.pill;
  const k = (i: number) => backOut(clamp((t - 3 - i * 5) / 10));
  const label = (x: number, y: number, s: string, size = 72, fill = S.fg) => <text x={x} y={y} textAnchor="middle" fontFamily={S.font} fontSize={size} fill={fill}>{s}</text>;
  const ab = [items[0] ?? 'YES', items[1] ?? 'NO'];
  switch (style) {
    case 'split':
      return (
        <g>
          <rect x={0} y={0} width={960 * k(0)} height={1080} fill={S.acc} opacity={0.22} />
          <rect x={1920 - 960 * k(1)} y={0} width={960 * k(1)} height={1080} fill={S.fg} opacity={0.14} />
          <line x1={960} y1={1080 * (1 - k(0))} x2={960} y2={1080} stroke={S.fg} strokeWidth={6} />
          {label(480, 560, ab[0], 96)}{label(1440, 560, ab[1], 96)}
        </g>
      );
    case 'stack':
      return <g>{ab.map((s, i) => <g key={i} transform={`translate(${(1 - k(i)) * -900} 0)`}><rect x={460} y={400 + i * 190} width={1000} height={150} rx={S.r} fill={S.bg} opacity={S.o} /><circle cx={540} cy={475 + i * 190} r={46} fill={S.acc} />{label(540, 498 + i * 190, i ? 'B' : 'A', 60, S.bg)}{label(1010, 500 + i * 190, s)}</g>)}</g>;
    case 'badge':
      return <g>{ab.map((s, i) => <g key={i} transform={`translate(${i ? 1300 : 620} 540) scale(${k(i)})`}><circle r={220} fill={S.bg} opacity={S.o} stroke={S.acc} strokeWidth={10} />{label(0, 24, s, 76)}</g>)}</g>;
    case 'ticket':
      return <g>{ab.map((s, i) => <g key={i} transform={`translate(${i ? 1340 : 580} ${540 + (1 - k(i)) * 700}) rotate(${i ? 4 : -4})`}><path d="M -300 -140 H 300 V -40 A 40 40 0 0 0 300 40 V 140 H -300 V 40 A 40 40 0 0 0 -300 -40 Z" fill={S.bg} opacity={S.o} stroke={S.acc} strokeWidth={6} strokeDasharray="18 12" />{label(0, 26, s, 76)}</g>)}</g>;
    default:
      return <g>{ab.map((s, i) => <g key={i} transform={`translate(${i ? 1340 : 580} 540) scale(${k(i)})`}><rect x={-320} y={-150} width={640} height={300} rx={S.r} fill={S.bg} opacity={S.o} stroke={S.acc} strokeWidth={6} />{label(0, 26, s, 80)}</g>)}</g>;
  }
};

export const SpecShot: React.FC<{ spec: Spec; t: number; len: number; f: number }> = ({ spec, t, len }) => {
  const uid = spec.id;
  const seed = spec.seed ?? 1;
  const set = SETS[spec.set] ?? SETS.study;
  const kind = spec.kind ?? 'scene';
  const cast = kind === 'scene' || kind === 'punch' ? spec.cast ?? [] : [];
  const marks = cast.map((c) => set.marks[(c.mark ?? 0) % Math.max(1, set.marks.length)]);
  const focus = marks[spec.focus ?? 0];
  const fr = move(spec.cam ?? 'static', t, len, frameFor(kind === 'punch' ? 'close' : spec.angle ?? 'wide', focus, marks[1]), seed);
  const camera = `${fr.rot ? `rotate(${fr.rot} 960 540) ` : ''}${camT(fr.cx, fr.cy, fr.z)}`;
  const satOf = (n?: string) => (n ? LIBRARY.lights[n] ?? [] : []).find((l) => l.sat !== undefined)?.sat;
  const sats = [satOf(spec.light), satOf(spec.tone ? `tone_${spec.tone}` : undefined)].filter((s): s is number => s !== undefined);
  const sat = sats.length ? sats.reduce((a, b) => a * b, 1) : undefined;
  const en = entry(spec.trans, t);
  const blurIn = spec.trans === 'blur' && t < 8 ? 14 * (1 - easeOut(clamp(t / 8))) : 0;
  const iris = spec.trans === 'iris' && t < 10;
  const rim = spec.light === 'night' || spec.light === 'moonlight' || spec.light === 'underwater' ? 'rimBlue' : spec.light === 'alarm' ? 'rimRed' : 'rimR';
  const head = focus ? { x: focus.x, y: focus.y - 176 * focus.scale } : { x: 960, y: 400 };
  const text = spec.text ?? [];

  const world = (
    <g transform={camera}>
      {kind === 'insert' ? (
        <>
          <Tabletop edge={spec.edge ?? 820} kind={seed % 2 ? 'stone' : 'wood'} />
          {(PROPS[spec.prop ?? 'Paper'] ?? PROPS.Paper)(960, 560, t, 2)}
        </>
      ) : (
        <set.Back t={t + (spec.tOff ?? 0)} v={spec.v ?? {}} id={uid} />
      )}
      {cast.map((c, i) => (
        <Hero key={i} look={LOOKS[(c.look ?? 'pipHood') as CastName] ?? LOOKS.pipHood} pose={act(c, marks[i], t, len, seed + i)} rimId={rim} />
      ))}
      {kind === 'scene' && spec.prop && focus ? (PROPS[spec.prop] ?? (() => null))(focus.x + 150 * focus.scale, focus.y + 135 * focus.scale, t, focus.scale) : null}
      {set.Front && kind !== 'insert' ? <set.Front t={t} v={spec.v ?? {}} /> : null}
      {kind === 'punch' ? <FocusRings x={head.x} y={head.y} t={t} /> : null}
      {kind === 'diagram' ? (
        <>
          <Panel t={t} text={text[0] ?? ''} skin={spec.skin} />
          {spec.num !== undefined ? <CountUp x={960} y={640} t={t - 6} to={spec.num} dur={36} size={170} /> : null}
          <Arrow x0={420} y0={820} x1={1500} y1={820} t={t - 4} dur={24} bend={-60} />
        </>
      ) : null}
    </g>
  );

  return (
    <g>
      <defs>
        <filter id={`cw${uid}`} x="-20%" width="140%"><feGaussianBlur stdDeviation="28 0" /></filter>
        {blurIn ? <filter id={`cb${uid}`}><feGaussianBlur stdDeviation={blurIn} /></filter> : null}
        {sat !== undefined ? <filter id={`cs${uid}`}><feColorMatrix type="saturate" values={String(sat)} /></filter> : null}
        {iris ? (
          <mask id={`ci${uid}`}>
            <rect width={1920} height={1080} fill="#000" />
            <circle cx={960} cy={540} r={1150 * easeOut(clamp(t / 10))} fill="#FFF" />
          </mask>
        ) : null}
      </defs>
      <g transform={en.tr} filter={en.whip ? `url(#cw${uid})` : blurIn ? `url(#cb${uid})` : undefined} mask={iris ? `url(#ci${uid})` : undefined}>
        <g filter={sat !== undefined ? `url(#cs${uid})` : undefined}>{world}</g>
        <Light name={spec.light} t={t} uid={uid} />
        <Light name={spec.tone ? `tone_${spec.tone}` : undefined} t={t} uid={`${uid}t`} />
        {kind === 'card' ? <Card t={t} lines={text} style={spec.title} /> : null}
        {kind === 'options' ? <Options t={t} items={spec.items ?? []} style={spec.opt} skin={spec.skin} /> : null}
        {spec.ots ? (
          <Foreground blur={10}>
            <Hero look={LOOKS[spec.ots as CastName] ?? LOOKS.mo} pose={{ ...basePose, x: 250, y: 1000, scale: 2.4, yaw: 0.85, facing: 1 }} />
          </Foreground>
        ) : null}
      </g>
      <Overlay name={spec.trans} t={t} uid={uid} />
    </g>
  );
};
