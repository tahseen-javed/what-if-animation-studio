import React from 'react';
import { Composition } from 'remotion';
import './engine/fonts';
import { STUDIO } from './studio.config';
import { EPISODES } from './episodes';
import { CastSheet } from './CastSheet';
import { PlanFilm, PlanBoard, DEMO } from './compiler/PlanFilm';

// Every episode gets two compositions: <Id> (the film) and <Id>Board (one frame per shot, at its key frame, for the
// storyboard). Cast renders the cast sheet.
//   npx remotion studio src/index.ts --port 3430

export const Root: React.FC = () => {
  const common = { width: STUDIO.width, height: STUDIO.height, fps: STUDIO.fps };
  return (
    <>
      {EPISODES.map((e) => (
        <React.Fragment key={e.id}>
          <Composition id={e.id} component={e.Main} durationInFrames={Math.max(1, e.total)} {...common} />
          <Composition id={`${e.id}Board`} component={e.Board} durationInFrames={Math.max(1, e.shotCount)} {...common} />
        </React.Fragment>
      ))}
      <Composition id="Cast" component={CastSheet} durationInFrames={1} {...common} />
      <Composition id="PlanFilm" component={PlanFilm} defaultProps={DEMO} durationInFrames={60} calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, props.plan.timeline.total) })} {...common} />
      <Composition id="PlanBoard" component={PlanBoard} defaultProps={DEMO} durationInFrames={1} calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, props.plan.timeline.shots.length) })} {...common} />
    </>
  );
};
