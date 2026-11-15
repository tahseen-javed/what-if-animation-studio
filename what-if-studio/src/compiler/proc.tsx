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
      {(d.plants ?? []).map(([u, w], i) => <FloorPlant key={i} r={R} u={u} w={w} />)}
      {(d.pend ?? []).map(([u, w], i) => <Pendant key={i} r={R} u={u} w={w} t={t} />)}
      <LightVeil id={`${id}v`} lights={lights} o={d.veil ?? 0.38} />
      {d.glow ? <Glow x={960} y={320} r={760} kind={d.glow} o={0.3} /> : null}
      <Dust t={t} seed={7} x0={600} y0={300} w={720} h={420} o={0.45} />
    </g>
  );
};
