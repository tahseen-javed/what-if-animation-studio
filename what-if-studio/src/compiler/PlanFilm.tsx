import React from 'react';
import { AbsoluteFill } from 'remotion';
import { Episode, Board, ShotMap, Timeline } from '../engine';
import { SpecShot, Spec } from './shot';

// A whole chapter as data: the director writes plan.json (timeline + one spec per shot + the video's DNA grade), and
// these two compositions render it: PlanFilm (the film) and PlanBoard (one still per shot, for the Doctor's sheet).
//   npx remotion render src/index.ts PlanFilm out.mp4 --props=plan.json
export type Plan = { plan: { id: string; dna: { grade?: string; grain?: boolean; vignette?: boolean; bg?: string }; timeline: Timeline; specs: Record<string, Spec> } };

export const DEMO: Plan = {
  plan: {
    id: 'demo',
    dna: {},
    timeline: { slug: 'demo', title: 'demo', fps: 30, total: 60, segments: [{ shot: 'S1', a: 0, b: 60, t0: 0, t1: 60 }], shots: [{ id: 'S1', size: 'medium', key: 30, len: 60, first: 0 }], fx: [], audio: {} },
    specs: { S1: { id: 'S1', set: 'kitchen', angle: 'medium', cam: 'pushIn', light: 'dusk', trans: 'whip', cast: [{ look: 'pipHood', pose: 'point' }] } },
  },
};

const useShots = (specs: Record<string, Spec>) =>
  React.useMemo(() => {
    const m: ShotMap = {};
    for (const [id, s] of Object.entries(specs)) m[id] = (p) => <SpecShot spec={s} {...p} />;
    return m;
  }, [specs]);

export const PlanFilm: React.FC<Plan> = ({ plan }) => {
  const shots = useShots(plan.specs);
  return (
    <AbsoluteFill style={{ filter: plan.dna.grade && plan.dna.grade !== 'none' ? plan.dna.grade : undefined }}>
      <Episode timeline={plan.timeline} shots={shots} grain={plan.dna.grain ?? true} vignette={plan.dna.vignette ?? true} bg={plan.dna.bg} />
    </AbsoluteFill>
  );
};

export const PlanBoard: React.FC<Plan> = ({ plan }) => {
  const shots = useShots(plan.specs);
  return (
    <AbsoluteFill style={{ filter: plan.dna.grade && plan.dna.grade !== 'none' ? plan.dna.grade : undefined }}>
      <Board timeline={plan.timeline} shots={shots} grain={plan.dna.grain ?? true} vignette={plan.dna.vignette ?? true} bg={plan.dna.bg} />
    </AbsoluteFill>
  );
};
