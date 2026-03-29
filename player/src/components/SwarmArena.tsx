import { useMemo } from "react";
import type { ConsumerSnapshot } from "../types";
import { computeSwarmLayout, getZoneRanges } from "../utils/swarmLayout";
import ConsumerDot from "./ConsumerDot";

const SVG_WIDTH = 800;
const SVG_HEIGHT = 600;

interface SwarmArenaProps {
  consumers: ConsumerSnapshot[];
}

export default function SwarmArena({ consumers }: SwarmArenaProps) {
  const positions = useMemo(
    () => computeSwarmLayout(consumers, SVG_WIDTH, SVG_HEIGHT),
    [consumers]
  );

  const zones = useMemo(() => getZoneRanges(SVG_WIDTH), []);

  return (
    <svg
      viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
      className="w-full h-full"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* Zone backgrounds */}
      {zones.map((z) => (
        <g key={z.zone}>
          <rect
            x={z.left}
            y={0}
            width={z.width}
            height={SVG_HEIGHT}
            rx={8}
            fill={
              z.zone === "ICE"
                ? "#fef2f2"
                : z.zone === "HYBRID"
                  ? "#eff6ff"
                  : "#ecfdf5"
            }
          />
          <text
            x={z.left + z.width / 2}
            y={24}
            textAnchor="middle"
            className="fill-gray-500 text-[13px] font-semibold"
          >
            {z.zone}
          </text>
        </g>
      ))}

      {/* Consumer dots */}
      {consumers.map((c) => {
        const pos = positions.get(c.id);
        if (!pos) return null;
        return (
          <ConsumerDot
            key={c.id}
            x={pos.x}
            y={pos.y}
            vehicle={c.vehicle}
            justBought={c.just_bought}
          />
        );
      })}
    </svg>
  );
}
