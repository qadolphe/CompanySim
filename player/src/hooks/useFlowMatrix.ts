import { useMemo } from "react";
import type { ConsumerSnapshot, VehicleType } from "../types";

const VEHICLE_TYPES: VehicleType[] = ["ICE", "HYBRID", "EV"];

export interface PoolCounts {
  ICE: number;
  HYBRID: number;
  EV: number;
}

/**
 * 3×3 matrix counting consumers that moved from one vehicle type to another.
 * `flows[from][to]` = number of consumers who held `from` last tick and now hold `to`.
 * Diagonal entries are "stayed" counts.
 */
export type FlowMatrix = Record<VehicleType, Record<VehicleType, number>>;

export interface FlowResult {
  pools: PoolCounts;
  flows: FlowMatrix;
  totalConsumers: number;
}

function emptyMatrix(): FlowMatrix {
  return {
    ICE: { ICE: 0, HYBRID: 0, EV: 0 },
    HYBRID: { ICE: 0, HYBRID: 0, EV: 0 },
    EV: { ICE: 0, HYBRID: 0, EV: 0 },
  };
}

function countPools(consumers: ConsumerSnapshot[]): PoolCounts {
  const counts: PoolCounts = { ICE: 0, HYBRID: 0, EV: 0 };
  for (const c of consumers) counts[c.vehicle]++;
  return counts;
}

/**
 * Computes the transition flow matrix between two consecutive ticks.
 *
 * Algorithm:
 * 1. Index previous tick's consumers by id → vehicle type (Map lookup)
 * 2. Iterate current tick's consumers, look up their previous vehicle
 * 3. Increment flows[prevVehicle][currentVehicle]
 *
 * Complexity: O(n) where n = number of consumers
 */
function computeFlows(
  prev: ConsumerSnapshot[],
  curr: ConsumerSnapshot[],
): FlowMatrix {
  const matrix = emptyMatrix();

  // Build lookup: id → vehicle for previous tick
  const prevMap = new Map<number, VehicleType>();
  for (const c of prev) {
    prevMap.set(c.id, c.vehicle);
  }

  // Count each consumer's transition
  for (const c of curr) {
    const prevVehicle = prevMap.get(c.id);
    if (prevVehicle !== undefined) {
      matrix[prevVehicle][c.vehicle]++;
    }
    // New consumers (if any) are ignored in the flow matrix
  }

  return matrix;
}

/**
 * Hook: computes pool counts and flow matrix between previous and current tick.
 * When there is no previous tick (step 0), flows are all zero.
 */
export function useFlowMatrix(
  currentConsumers: ConsumerSnapshot[],
  previousConsumers: ConsumerSnapshot[] | null,
): FlowResult {
  return useMemo(() => {
    const pools = countPools(currentConsumers);
    const flows =
      previousConsumers !== null
        ? computeFlows(previousConsumers, currentConsumers)
        : emptyMatrix();

    return { pools, flows, totalConsumers: currentConsumers.length };
  }, [currentConsumers, previousConsumers]);
}

/** Utility: extract only the off-diagonal (actual transition) entries */
export function getTransitions(
  flows: FlowMatrix,
): { from: VehicleType; to: VehicleType; count: number }[] {
  const result: { from: VehicleType; to: VehicleType; count: number }[] = [];
  for (const from of VEHICLE_TYPES) {
    for (const to of VEHICLE_TYPES) {
      if (from !== to && flows[from][to] > 0) {
        result.push({ from, to, count: flows[from][to] });
      }
    }
  }
  return result;
}
