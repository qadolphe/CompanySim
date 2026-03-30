import { useState, useEffect, useRef } from "react";
import type { VehicleType } from "../types";
import type { FlowMatrix } from "./useFlowMatrix";
import { getTransitions } from "./useFlowMatrix";

/** 1 representative particle per RATIO actual consumers */
const CONSUMERS_PER_PARTICLE = 500;

export interface FlowParticleData {
  id: string;
  from: VehicleType;
  to: VehicleType;
}

/**
 * Converts off-diagonal flow-matrix entries into a capped array of
 * representative particles, then auto-clears them after `durationMs`.
 */
export function useFlowParticles(
  flows: FlowMatrix,
  step: number,
  durationMs = 800,
): FlowParticleData[] {
  const [particles, setParticles] = useState<FlowParticleData[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    // Clear any in-flight timer from previous step
    if (timerRef.current) clearTimeout(timerRef.current);

    const transitions = getTransitions(flows);
    const batch: FlowParticleData[] = [];

    for (const { from, to, count } of transitions) {
      const numDots = Math.max(1, Math.round(count / CONSUMERS_PER_PARTICLE));
      for (let i = 0; i < numDots; i++) {
        batch.push({
          id: `${step}-${from}-${to}-${i}`,
          from,
          to,
        });
      }
    }

    setParticles(batch);

    // Auto-clear after animation completes
    if (batch.length > 0) {
      timerRef.current = setTimeout(() => setParticles([]), durationMs);
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [flows, step, durationMs]);

  return particles;
}
