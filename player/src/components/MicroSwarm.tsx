import type { Tick } from "../types";
import SwarmArena from "./SwarmArena";

interface MicroSwarmProps {
  tick: Tick;
}

export default function MicroSwarm({ tick }: MicroSwarmProps) {
  return (
    <div className="flex flex-col p-4 min-h-0">
      <div className="flex-1 min-h-0">
        <SwarmArena consumers={tick.micro_state} />
      </div>

      {/* Legend */}
      <div className="flex justify-center gap-6 pt-3 text-sm text-gray-600">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full bg-rose-400" />
          ICE
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full bg-blue-400" />
          HYBRID
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full bg-emerald-400" />
          EV
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full border-2 border-emerald-400 bg-transparent" />
          Just Bought
        </span>
      </div>
    </div>
  );
}
