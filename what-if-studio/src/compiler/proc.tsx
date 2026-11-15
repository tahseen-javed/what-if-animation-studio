import React from 'react';
import { makeRoom, RoomShell, BackWindow, Pendant, WallLight, Box, FloorShadow, FloorPlant, WallFrame, WallClock, LightVeil, Dust, Glow, stand } from '../engine';

// Procedural interiors: one data entry in library.json "proc" = one room built from the room kit (shell, window,
// lights, furniture boxes with shelf/rack detail, dressing, light veil). Library growth without new drawing code.
type BoxDef = [number, number, number, number, number, number, string, (string | null)?, ('shelf' | 'rack' | null)?];
export type ProcDef = {
  theme: string; vp: [number, number]; back: [number, number, number, number]; depth?: number; floor?: 'boards' | 'tiles';
  wall?: string; side?: string; floorC?: string; ceiling?: string; win?: [number, number, number, number]; night?: boolean; cols?: number; sky?: 'day' | 'blinds';
  pend?: [number, number][]; lamps?: [number, number, number][]; boxes?: BoxDef[]; plants?: [number, number][];
  frames?: [number, number, number, number][]; clock?: [number, number]; glow?: 'warm' | 'cool' | 'red'; veil?: number;
  items?: (string | number)[][];
};

type Rm = ReturnType<typeof makeRoom>;
const poly = (R: Rm, q: number[][]) => q.map(([u, v, w]) => { const p = R.P(u, v, w); return `${p.x},${p.y}`; }).join(' ');
const shade = (c: string, k: number) => `#${[1, 3, 5].map((i) => Math.max(0, Math.min(255, Math.round(parseInt(c.slice(i, i + 2), 16) * k))).toString(16).padStart(2, '0')).join('')}`;

/** Structural pieces: ['table'|'sofa'|'bed', u0, u1, w0, w1, colour], ['screen', u0, u1, v0, v1, colour],
 *  ['column', u, w, colour], ['alcove', 'L'|'R', w0, w1, v0] (an opening in a side wall: an L-shaped room),
 *  ['mezz', w1, colour] (a balcony across the back with railings and stairs). */
const Item: React.FC<{ R: Rm; it: (string | number)[]; t: number }> = ({ R, it, t }) => {
  const [k, a, b, c, e, col] = it as [string, number, number, number, number, string];
  const B = (u: [number, number], v: [number, number], w: [number, number], f: string) => <Box r={R} u={u} v={v} w={w} front={f} top={shade(f, 1.2)} side={shade(f, 0.75)} rim />;
  const leg = (u: number, w: number, v0: number) => { const p = R.P(u, v0, w); const q = R.P(u, 1, w); return <line x1={p.x} y1={p.y} x2={q.x} y2={q.y} stroke={shade(col ?? '#555555', 0.6)} strokeWidth={6} />; };
  switch (k) {
    case 'table':
      return <g>{leg(a + 0.01, c + 0.01, 0.8)}{leg(b - 0.01, c + 0.01, 0.8)}{B([a, b], [0.78, 0.8], [c, e], col)}{leg(a + 0.01, e - 0.01, 0.8)}{leg(b - 0.01, e - 0.01, 0.8)}</g>;
    case 'sofa':
      return <g>{B([a, b], [0.7, 1], [c, c + 0.04], shade(col, 0.85))}{B([a, b], [0.86, 1], [c, e], col)}{B([a, a + 0.03], [0.8, 1], [c, e], shade(col, 0.9))}{B([b - 0.03, b], [0.8, 1], [c, e], shade(col, 0.9))}</g>;
    case 'bed':
      return <g>{B([a, b], [0.66, 1], [c, c + 0.02], shade(col, 0.6))}{B([a, b], [0.88, 1], [c, e], '#EDE7DA')}{B([a, b], [0.86, 0.9], [c + (e - c) * 0.35, e], col)}{B([a + 0.02, a + (b - a) * 0.45], [0.84, 0.88], [c + 0.02, c + 0.08], '#FFFFFF')}</g>;
    case 'screen': {
      const fl = 0.75 + 0.25 * Math.sin(t / 5);
      return <g>{B([a, b], [c, e], [0, 0.015], '#15171C')}<polygon points={poly(R, [[a + 0.01, c + 0.02, 0.016], [b - 0.01, c + 0.02, 0.016], [b - 0.01, e - 0.02, 0.016], [a + 0.01, e - 0.02, 0.016]])} fill={col} opacity={fl} /></g>;
    }
    case 'column':
      return B([a - 0.025, a + 0.025], [0, 1], [b, b + 0.04], col ?? '#BFB8AA');
    case 'alcove': {
      const u = it[1] === 'L' ? 0 : 1;
      const [w0, w1, v0] = [b, c, e];
      return <g><polygon points={poly(R, [[u, v0, w0], [u, v0, w1], [u, 1, w1], [u, 1, w0]])} fill="#0B0A10" opacity={0.85} /><polygon points={poly(R, [[u, v0 + 0.03, w0 + 0.02], [u, v0 + 0.03, w1 - 0.02], [u, 0.97, w1 - 0.02], [u, 0.97, w0 + 0.02]])} fill="#F2C46D" opacity={0.18} /></g>;
    }
    case 'mezz': {
      const w1 = a as number;
      const f = (b as unknown as string) ?? '#6B5A48';
      return (
        <g>
          {B([0, 1], [0.4, 0.46], [0, w1], f)}
          {Array.from({ length: 13 }, (_, i) => { const p = R.P(i / 12, 0.4, w1); const q = R.P(i / 12, 0.32, w1); return <line key={i} x1={p.x} y1={p.y} x2={q.x} y2={q.y} stroke={shade(f, 0.6)} strokeWidth={4} />; })}
          <polyline points={poly(R, [[0, 0.32, w1], [1, 0.32, w1]])} stroke={shade(f, 0.6)} strokeWidth={6} fill="none" />
          {[0, 1, 2, 3, 4, 5].map((s) => B([0.86, 0.96], [0.46 + s * 0.09, 1], [w1 + s * 0.03, w1 + (s + 1) * 0.03], shade(f, 0.9)))}
        </g>
      );
    }
    default:
      return null;
  }
};

const room = (d: ProcDef) => makeRoom({ x: d.vp[0], y: d.vp[1] }, { x0: d.back[0], x1: d.back[1], y0: d.back[2], y1: d.back[3] }, d.depth ?? 3.4);
export const procMarks = (d: ProcDef) => [[0.3, 0.55], [0.5, 0.5], [0.7, 0.55]].map(([u, w]) => stand(room(d), u, w));
const BOOKS = ['#B5543C', '#3E7CB1', '#D9A441', '#5B8C5A', '#8E5BA6', '#E7DCC8'];

export const ProcSet: React.FC<{ d: ProcDef; t: number; id: string }> = ({ d, t, id }) => {
  const R = room(d);
  const lights: [number, number, number][] = (d.pend ?? []).map(([u, w]) => {
    const p = R.P(u, 0.27, w);
    return [p.x, p.y + 60, 300];
  });
  if (d.win) lights.push([(d.win[0] + d.win[1]) / 2, (d.win[2] + d.win[3]) / 2, 280]);
  return (
    <g>
      <RoomShell r={R} id={id} floor={d.floor ?? 'boards'} wall={d.wall} side={d.side} floorC={d.floorC} ceiling={d.ceiling} />
      {d.win ? <BackWindow r={R} id={`${id}w`} t={t} x0={d.win[0]} x1={d.win[1]} y0={d.win[2]} y1={d.win[3]} cols={d.cols ?? 2} curtains night={d.night} sun={{ x: (d.win[0] + d.win[1]) / 2, y: d.win[3] - 30 }} /> : null}
      {d.win && d.sky === 'day' ? <rect x={d.win[0]} y={d.win[2]} width={d.win[1] - d.win[0]} height={d.win[3] - d.win[2]} fill="#9FD3FF" opacity={0.55} style={{ mixBlendMode: 'screen' }} /> : null}
      {d.win && d.sky === 'blinds'
        ? Array.from({ length: Math.floor((d.win[3] - d.win[2]) / 16) }, (_, i) => (
            <rect key={i} x={d.win![0]} y={d.win![2] + i * 16} width={d.win![1] - d.win![0]} height={10} fill="#D8D2C4" opacity={0.92} />
          ))
        : null}
      {(d.frames ?? []).map(([x, y, w, h], i) => <WallFrame key={i} x={x} y={y} w={w} h={h} art={(i % 3) as 0 | 1 | 2} />)}
      {d.clock ? <WallClock x={d.clock[0]} y={d.clock[1]} t={t} /> : null}
      {(d.lamps ?? []).map(([u, v, w], i) => <WallLight key={i} r={R} u={u} v={v} w={w} />)}
      {(d.boxes ?? []).map(([u0, u1, v0, v1, w0, w1, c, top, kind], i) => (
        <g key={i}>
          <FloorShadow r={R} u={[u0, u1]} w={[w0, w1]} />
          <Box r={R} u={[u0, u1]} v={[v0, v1]} w={[w0, w1]} front={c} top={top ?? c} side={c} rim />
          {kind
            ? [1, 2, 3, 4].map((k) => {
                const v = v0 + ((v1 - v0) * k) / 5;
                const a = R.P(u0, v, w1);
                const b = R.P(u1, v, w1);
                const h = (R.P(u0, v0 + (v1 - v0) / 5, w1).y - R.P(u0, v0, w1).y) * 0.75;
                return (
                  <g key={k}>
                    <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#000" strokeOpacity={0.45} strokeWidth={3} />
                    {kind === 'shelf'
                      ? Array.from({ length: Math.max(3, Math.floor((b.x - a.x) / 26)) }, (_, j) => (
                          <rect key={j} x={a.x + 6 + j * 26} y={a.y - h} width={20} height={h * (0.7 + 0.3 * Math.abs(Math.sin(j * 7.3 + k)))} fill={BOOKS[(j + k * 3 + i) % BOOKS.length]} opacity={0.85} transform={`translate(0 ${h * 0.3 * (1 - Math.abs(Math.sin(j * 7.3 + k)))})`} />
                        ))
                      : [0, 1, 2].map((j) => <circle key={j} cx={a.x + 18 + j * 16} cy={a.y - h / 2} r={4} fill={j === 2 ? '#3FA9F5' : '#39FF7A'} opacity={(Math.sin(t / 3 + j * 2 + k * 5 + i) + 1) / 2} />)}
                  </g>
                );
              })
            : null}
        </g>
      ))}
      {(d.items ?? []).map((it, i) => <Item key={i} R={R} it={it} t={t} />)}
      {(d.plants ?? []).map(([u, w], i) => <FloorPlant key={i} r={R} u={u} w={w} />)}
      {(d.pend ?? []).map(([u, w], i) => <Pendant key={i} r={R} u={u} w={w} t={t} />)}
      <LightVeil id={`${id}v`} lights={lights} o={d.veil ?? 0.38} />
      {d.glow ? <Glow x={960} y={320} r={760} kind={d.glow} o={0.3} /> : null}
      <Dust t={t} seed={7} x0={600} y0={300} w={720} h={420} o={0.45} />
    </g>
  );
};
