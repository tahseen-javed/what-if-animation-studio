import React from 'react';
import {
  Study, STUDY, Kitchen, KITCHEN, KitchenIsland, Lounge, LOUNGE, Bedroom, BEDROOM, Classroom, Rooftop, Stairwell, Banister,
  hipGround, Apartments, Schematic, stand, Room,
} from '../engine';

// Set adapters: how the compiler draws each library set and where characters can stand on it (marks: hip point and
// scale). A new set = one entry here + one entry in library.json (theme, variants). Front is drawn after the cast.
export type Mark = { x: number; y: number; scale: number };
export type V = Record<string, number | boolean | string>;
export type SetDef = { Back: React.FC<{ t: number; v: V; id: string }>; Front?: React.FC<{ t: number; v: V }>; marks: Mark[] };

const n = (x: unknown, d: number) => (typeof x === 'number' ? x : d);
const st = (r: Room, list: [number, number][]) => list.map(([u, w]) => stand(r, u, w));

export const SETS: Record<string, SetDef> = {
  study: { Back: ({ t, v, id }) => <Study t={t} id={id} night={!!v.night} veil={n(v.veil, 0)} />, marks: st(STUDY, [[0.32, 0.55], [0.52, 0.5], [0.72, 0.55]]) },
  kitchen: {
    Back: ({ t, v, id }) => <Kitchen t={t} id={id} veil={n(v.veil, 0)} red={n(v.red, 0)} />,
    Front: () => <KitchenIsland />,
    marks: st(KITCHEN, [[0.3, 0.4], [0.5, 0.4], [0.7, 0.4]]),
  },
  lounge: { Back: ({ t, v, id }) => <Lounge t={t} id={id} veil={n(v.veil, 0)} tv={n(v.tv, 0)} />, marks: st(LOUNGE, [[0.3, 0.55], [0.5, 0.5], [0.7, 0.55]]) },
  bedroom: { Back: ({ t, v, id }) => <Bedroom t={t} id={id} veil={n(v.veil, 0)} lamp={n(v.lamp, 1)} />, marks: st(BEDROOM, [[0.55, 0.55], [0.68, 0.5], [0.8, 0.55]]) },
  classroom: {
    Back: ({ t, v, id }) => <Classroom t={t} id={id} laugh={n(v.laugh, 0)} />,
    marks: [{ x: 1260, y: 760, scale: 1 }, { x: 1090, y: 770, scale: 1.02 }, { x: 1430, y: 770, scale: 1.02 }],
  },
  rooftop: {
    Back: ({ t, v }) => <Rooftop t={t} sunY={n(v.sunY, 640)} red={n(v.red, 0)} cityLit={n(v.cityLit, 1)} />,
    marks: [700, 960, 1220].map((x) => ({ x, y: 820 - 140, scale: 1 })),
  },
  stairwell: { Back: ({ t, id }) => <Stairwell t={t} id={id} />, Front: () => <Banister />, marks: [640, 900, 1160].map((x) => ({ x, y: hipGround(x), scale: 0.9 })) },
  apartments: { Back: ({ t, v, id }) => <Apartments t={t} id={id} seed={n(v.seed, 9)} others={n(v.others, 0.3)} />, marks: [] },
  schematic: { Back: ({ t, id }) => <Schematic t={t} id={id} />, marks: [] },
};
