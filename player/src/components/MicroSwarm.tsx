import type { Tick } from "../types";
import AggregateSwarm from "./AggregateSwarm";

interface MicroSwarmProps {
  tick: Tick;
  prevTick: Tick | null;
}

export default function MicroSwarm({ tick, prevTick }: MicroSwarmProps) {
  return (
    <div className="flex flex-col p-4 min-h-0">
      <div className="flex-1 min-h-0">
        <AggregateSwarm tick={tick} prevTick={prevTick} />
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
          <span className="inline-block w-3 h-3 rounded-full border-2 border-yellow-400 bg-yellow-100" />
          Flow (1 dot ≈ 500)
        </span>
      </div>
    </div>
  );
}
