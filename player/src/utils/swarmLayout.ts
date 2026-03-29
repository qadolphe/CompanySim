import type { ConsumerSnapshot } from "../types";

const ZONE_ORDER: ConsumerSnapshot["vehicle"][] = ["ICE", "HYBRID", "EV"];
const ZONE_GAP = 20;
const DOT_RADIUS = 4;
const DOT_SPACING = 11;

export interface DotPosition {
  x: number;
  y: number;
}

/**
 * Deterministic layout: splits consumers into 3 zone columns and
 * packs dots into a grid within each column.
 */
export function computeSwarmLayout(
  consumers: ConsumerSnapshot[],
  width: number,
  _height: number
): Map<number, DotPosition> {
  const positions = new Map<number, DotPosition>();

  // Group by vehicle type
  const groups: Record<string, ConsumerSnapshot[]> = { ICE: [], HYBRID: [], EV: [] };
  for (const c of consumers) {
    groups[c.vehicle].push(c);
  }

  const zoneWidth = (width - ZONE_GAP * (ZONE_ORDER.length + 1)) / ZONE_ORDER.length;
  const topPadding = 40;

  for (let z = 0; z < ZONE_ORDER.length; z++) {
    const zone = ZONE_ORDER[z];
    const members = groups[zone];
    const zoneLeft = ZONE_GAP + z * (zoneWidth + ZONE_GAP);

    const cols = Math.max(1, Math.floor(zoneWidth / DOT_SPACING));
    const startX = zoneLeft + (zoneWidth - cols * DOT_SPACING) / 2 + DOT_RADIUS;

    for (let i = 0; i < members.length; i++) {
      const col = i % cols;
      const row = Math.floor(i / cols);
      positions.set(members[i].id, {
        x: startX + col * DOT_SPACING,
        y: topPadding + row * DOT_SPACING + DOT_RADIUS,
      });
    }
  }

  return positions;
}

export function getZoneRanges(
  width: number
): { zone: string; left: number; width: number }[] {
  const zoneWidth = (width - ZONE_GAP * (ZONE_ORDER.length + 1)) / ZONE_ORDER.length;
  return ZONE_ORDER.map((zone, z) => ({
    zone,
    left: ZONE_GAP + z * (zoneWidth + ZONE_GAP),
    width: zoneWidth,
  }));
}

export { DOT_RADIUS };
