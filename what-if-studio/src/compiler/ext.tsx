import React from 'react';
import { rnd } from '../engine';

// Procedural exteriors: one data entry in library.json "ext" = one outdoor place (sky, sun/moon/stars, layered
// silhouettes, ground, themed props). Characters stand on the ground at y 880.
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
  const [k, y, n, col, s, alt] = it as [string, number, number, string, number, string];
  const xs = Array.from({ length: n ?? 0 }, (_, i) => (i + 0.5) * (1920 / n) + (rnd(s ?? 3, i) - 0.5) * (1920 / n) * 0.6);
  switch (k) {
    case 'trees':
      return <g>{xs.map((x, i) => { const h = 120 + 90 * rnd(s, i + 9); return <g key={i}><rect x={x - 7} y={y - h * 0.35} width={14} height={h * 0.35} fill="#3B2A1E" /><path d={`M${x - h * 0.3} ${y - h * 0.3} L${x} ${y - h} L${x + h * 0.3} ${y - h * 0.3} Z`} fill={col} /></g>; })}</g>;
    case 'cacti':
      return <g>{xs.map((x, i) => { const h = 70 + 60 * rnd(s, i); return <g key={i} fill={col}><rect x={x - 9} y={y - h} width={18} height={h} rx={9} /><rect x={x - 30} y={y - h * 0.7} width={12} height={h * 0.35} rx={6} /><rect x={x - 30} y={y - h * 0.42} width={26} height={10} rx={5} /></g>; })}</g>;
    case 'rocks':
      return <g>{xs.map((x, i) => <ellipse key={i} cx={x} cy={y} rx={40 + 50 * rnd(s, i)} ry={18 + 22 * rnd(s, i + 4)} fill={col} />)}</g>;
    case 'buildings':
      return <g>{xs.map((x, i) => { const h = 180 + 260 * rnd(s, i); const w = 1920 / n * 0.8; return <g key={i}><rect x={x - w / 2} y={y - h} width={w} height={h} fill={col} />{Array.from({ length: 12 }, (_, j) => <rect key={j} x={x - w / 2 + 14 + (j % 3) * (w / 3.2)} y={y - h + 24 + Math.floor(j / 3) * 46} width={w / 6} height={22} fill={alt ?? '#FFD27A'} opacity={rnd(s + i, j) > 0.45 ? 0.85 : 0.08} />)}</g>; })}</g>;
    case 'stalls':
      return <g>{xs.map((x, i) => <g key={i}><rect x={x - 90} y={y - 120} width={180} height={120} fill="#5C4033" />{[0, 1, 2, 3, 4, 5].map((j) => <rect key={j} x={x - 105 + j * 35} y={y - 170} width={35} height={55} fill={j % 2 ? col : alt ?? '#FFFFFF'} />)}<rect x={x - 80} y={y - 70} width={160} height={30} fill={['#E4572E', '#F3A712', '#76B041'][i % 3]} /></g>)}</g>;
    case 'lamps':
      return <g>{xs.map((x, i) => <g key={i}><rect x={x - 5} y={y - 260} width={10} height={260} fill="#22252B" /><circle cx={x} cy={y - 262} r={16} fill="#FFE6A6" /><circle cx={x} cy={y - 262} r={90} fill="#FFD27A" opacity={0.18} /></g>)}</g>;
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
