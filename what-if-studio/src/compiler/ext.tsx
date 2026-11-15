import React from 'react';
import { rnd } from '../engine';

// Procedural exteriors: one data entry in library.json "ext" = one outdoor place (sky, sun/moon/stars, layered
// silhouettes, ground, themed props). Items: [kind, y, count, colour, seed, alt colour, size]; later items are nearer.
export type ExtDef = {
  theme: string; sky: [string, string]; horizon: number; ground: [string, string]; sun?: [number, number, number, string]; stars?: number;
  ridges?: [number, number, number, string][]; items?: (string | number)[][]; haze?: string;
};
export const extMarks = [640, 960, 1280].map((x) => ({ x, y: 880 - 140 * 1.05, scale: 1.05 }));

const ridge = (y: number, amp: number, s: number) => {
  let d = `M0 1080 L0 ${y}`;
  for (let x = 0; x <= 1920; x += 40) d += ` L${x} ${(y - amp * (0.5 + 0.5 * Math.sin(x / 170 + s) * Math.cos(x / 97 + s * 2)) - amp * 0.3 * rnd(s, x)).toFixed(1)}`;
  return `${d} L1920 1080 Z`;
};

const Items: React.FC<{ it: (string | number)[]; t: number }> = ({ it, t }) => {
  const [k, y, n, col, s, alt, zz] = it as [string, number, number, string, number, string, number];
  const z = zz ?? 1;
  const xs = Array.from({ length: n ?? 0 }, (_, i) => (i + 0.5) * (1920 / n) + (rnd(s ?? 3, i) - 0.5) * (1920 / n) * 0.6);
  switch (k) {
    case 'trees':
      return <g>{xs.map((x, i) => { const h = (120 + 90 * rnd(s, i + 9)) * z; return <g key={i}><rect x={x - 7 * z} y={y - h * 0.35} width={14 * z} height={h * 0.35} fill="#3B2A1E" /><path d={`M${x - h * 0.3} ${y - h * 0.3} L${x} ${y - h} L${x + h * 0.3} ${y - h * 0.3} Z`} fill={col} /></g>; })}</g>;
    case 'palms':
      return <g>{xs.map((x, i) => { const h = (220 + 80 * rnd(s, i)) * z; return <g key={i}><path d={`M${x} ${y} Q${x + 30 * z} ${y - h / 2} ${x + 10 * z} ${y - h}`} stroke="#6B4A2E" strokeWidth={14 * z} fill="none" />{[-1, -0.4, 0.3, 1].map((a, j) => <path key={j} d={`M${x + 10 * z} ${y - h} q${a * 90 * z} ${-30 * z} ${a * 150 * z} ${40 * z}`} stroke={col} strokeWidth={18 * z} fill="none" strokeLinecap="round" />)}</g>; })}</g>;
    case 'cacti':
      return <g>{xs.map((x, i) => { const h = (70 + 60 * rnd(s, i)) * z; const w = 18 * z; return <g key={i} fill={col}><rect x={x - w / 2} y={y - h} width={w} height={h} rx={w / 2} /><rect x={x - w * 1.7} y={y - h * 0.7} width={w * 0.7} height={h * 0.35} rx={w / 3} /><rect x={x - w * 1.7} y={y - h * 0.42} width={w * 1.4} height={w * 0.55} rx={w / 4} /><rect x={x + w} y={y - h * 0.8} width={w * 0.7} height={h * 0.3} rx={w / 3} /><rect x={x + w * 0.4} y={y - h * 0.55} width={w * 1.2} height={w * 0.55} rx={w / 4} /></g>; })}</g>;
    case 'rocks':
      return <g>{xs.map((x, i) => { const rx = (40 + 50 * rnd(s, i)) * z; const ry = (18 + 22 * rnd(s, i + 4)) * z; return <g key={i}><ellipse cx={x} cy={y} rx={rx} ry={ry} fill={col} /><ellipse cx={x - rx * 0.25} cy={y - ry * 0.35} rx={rx * 0.5} ry={ry * 0.35} fill="#FFFFFF" opacity={0.12} /></g>; })}</g>;
    case 'buildings':
      return <g>{xs.map((x, i) => { const h = (180 + 260 * rnd(s, i)) * z; const w = (1920 / n) * 0.8; return <g key={i}><rect x={x - w / 2} y={y - h} width={w} height={h} fill={col} />{Array.from({ length: 18 }, (_, j) => <rect key={j} x={x - w / 2 + 14 + (j % 3) * (w / 3.2)} y={y - h + 24 + Math.floor(j / 3) * 46} width={w / 6} height={22} fill={alt ?? '#FFD27A'} opacity={y - h + 24 + Math.floor(j / 3) * 46 < y - 30 && rnd(s + i, j) > 0.35 ? 0.9 : 0.06} />)}</g>; })}</g>;
    case 'neon':
      return <g>{xs.map((x, i) => <g key={i}><rect x={x - 70 * z} y={y - 40 * z} width={140 * z} height={50 * z} rx={10} fill="none" stroke={i % 2 ? col : alt ?? '#2FE0FF'} strokeWidth={6} opacity={0.6 + 0.4 * Math.abs(Math.sin(t / 7 + i))} /><rect x={x - 90 * z} y={y - 60 * z} width={180 * z} height={90 * z} fill={i % 2 ? col : alt ?? '#2FE0FF'} opacity={0.12} /></g>)}</g>;
    case 'stalls':
      return <g>{xs.map((x, i) => { const w = 180 * z; const h = 120 * z; return <g key={i}><path d={`M${x + w / 2} ${y - h} l${30 * z} ${-20 * z} v${h} l${-30 * z} ${20 * z} Z`} fill="#3E2A20" /><rect x={x - w / 2} y={y - h} width={w} height={h} fill="#5C4033" />{[0, 1, 2, 3, 4, 5].map((j) => <path key={j} d={`M${x - w / 2 - 15 * z + j * (w + 30 * z) / 6} ${y - h - 50 * z} h${(w + 30 * z) / 6} l${8 * z} ${50 * z} h${-(w + 30 * z) / 6} Z`} fill={j % 2 ? col : alt ?? '#FFFFFF'} />)}<rect x={x - w / 2 + 10} y={y - h * 0.55} width={w - 20} height={h * 0.25} fill={['#E4572E', '#F3A712', '#76B041'][i % 3]} />{[0, 1, 2].map((j) => <circle key={j} cx={x - w / 3 + j * w / 3} cy={y - h * 0.62} r={10 * z} fill={['#F94144', '#F9C74F', '#90BE6D'][(i + j) % 3]} />)}</g>; })}</g>;
    case 'lamps':
      return <g>{xs.map((x, i) => <g key={i}><rect x={x - 6 * z} y={y - 280 * z} width={12 * z} height={280 * z} fill={alt ?? '#6B7280'} /><rect x={x - 6 * z} y={y - 280 * z} width={60 * z} height={8 * z} fill={alt ?? '#6B7280'} /><circle cx={x + 52 * z} cy={y - 266 * z} r={14 * z} fill="#FFE6A6" /><circle cx={x + 52 * z} cy={y - 266 * z} r={110 * z} fill={col} opacity={0.22} /><ellipse cx={x + 52 * z} cy={y} rx={120 * z} ry={22 * z} fill={col} opacity={0.18} /></g>)}</g>;
    case 'fence':
      return <g>{Array.from({ length: 33 }, (_, i) => <rect key={i} x={i * 60} y={y - 70 * z} width={12} height={70 * z} fill={col} />)}<rect x={0} y={y - 55 * z} width={1920} height={8} fill={col} /><rect x={0} y={y - 25 * z} width={1920} height={8} fill={col} /></g>;
    case 'boats':
      return <g>{xs.map((x, i) => <g key={i}><path d={`M${x - 70 * z} ${y} h${140 * z} l${-20 * z} ${28 * z} h${-100 * z} Z`} fill={col} /><rect x={x - 3} y={y - 90 * z} width={6} height={90 * z} fill="#3B2A1E" /><path d={`M${x + 3} ${y - 88 * z} l${55 * z} ${70 * z} h${-55 * z} Z`} fill={alt ?? '#FFFFFF'} /></g>)}</g>;
    case 'lava':
      return <g><path d={`M${y} ${n} q60 120 -20 260 q80 60 40 160`} stroke={col} strokeWidth={26} fill="none" opacity={0.85} /><circle cx={y} cy={n} r={120} fill={col} opacity={0.25 + 0.1 * Math.sin(t / 6)} /></g>;
    case 'road':
      return <g><path d={`M${960 - 60} ${y} L${960 + 60} ${y} L${1500} 1080 L${420} 1080 Z`} fill={col} />{[0, 1, 2, 3].map((j) => <rect key={j} x={955} y={y + 30 + j * 70 + j * j * 8} width={10} height={30 + j * 12} fill={alt ?? '#F2E3A0'} />)}</g>;
    case 'waves':
      return <g>{[0, 1, 2, 3, 4].map((j) => <path key={j} d={Array.from({ length: 49 }, (_, i) => `${i ? 'L' : 'M'}${i * 40} ${y + j * 34 + 6 * Math.sin(i * 0.8 + t / 8 + j)}`).join(' ')} stroke={col} strokeWidth={4} fill="none" opacity={0.6 - j * 0.08} />)}</g>;
    case 'planet':
      return <g><circle cx={y} cy={n} r={s} fill={col} /><ellipse cx={y} cy={n} rx={s * 1.7} ry={s * 0.35} fill="none" stroke={alt ?? '#E8D8B0'} strokeWidth={8} opacity={0.7} /></g>;
    default:
      return null;
  }
};

export const ExtSet: React.FC<{ d: ExtDef; t: number; id: string }> = ({ d, t, id }) => (
  <g>
    <defs>
      <linearGradient id={`${id}s`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={d.sky[0]} /><stop offset="100%" stopColor={d.sky[1]} /></linearGradient>
      <linearGradient id={`${id}g`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={d.ground[0]} /><stop offset="100%" stopColor={d.ground[1]} /></linearGradient>
      <radialGradient id={`${id}u`}><stop offset="0%" stopColor={d.sun?.[3] ?? '#FFF'} stopOpacity={0.55} /><stop offset="100%" stopColor={d.sun?.[3] ?? '#FFF'} stopOpacity={0} /></radialGradient>
    </defs>
    <rect width={1920} height={1080} fill={`url(#${id}s)`} />
    {Array.from({ length: d.stars ?? 0 }, (_, i) => <circle key={i} cx={rnd(11, i) * 1920} cy={rnd(29, i) * d.horizon * 0.9} r={1 + 1.5 * rnd(5, i)} fill="#FFFFFF" opacity={0.4 + 0.6 * Math.abs(Math.sin(t / 9 + i))} />)}
    {d.sun ? <g><circle cx={d.sun[0]} cy={d.sun[1]} r={d.sun[2] * 3} fill={`url(#${id}u)`} /><circle cx={d.sun[0]} cy={d.sun[1]} r={d.sun[2]} fill={d.sun[3]} /></g> : null}
    {(d.ridges ?? []).map(([y, a, s, c], i) => <path key={i} d={ridge(y, a, s)} fill={c} />)}
    <rect x={0} y={d.horizon} width={1920} height={1080 - d.horizon} fill={`url(#${id}g)`} />
    {d.haze ? <rect x={0} y={d.horizon - 80} width={1920} height={160} fill={d.haze} opacity={0.25} /> : null}
    {(d.items ?? []).map((it, i) => <Items key={i} it={it} t={t} />)}
  </g>
);
