import { motion, AnimatePresence } from "framer-motion";
import type { Tick, VehicleType } from "../types";
import { useFlowMatrix } from "../hooks/useFlowMatrix";
import { useFlowParticles } from "../hooks/useFlowParticles";
import type { FlowParticleData } from "../hooks/useFlowParticles";

const ZONE_ORDER: VehicleType[] = ["ICE", "HYBRID", "EV"];

const ZONE_COLORS: Record<VehicleType, { bg: string; bar: string; glow: string; text: string }> = {
  ICE: { bg: "bg-rose-50", bar: "bg-rose-400", glow: "shadow-rose-400/40", text: "text-rose-600" },
  HYBRID: { bg: "bg-blue-50", bar: "bg-blue-400", glow: "shadow-blue-400/40", text: "text-blue-600" },
  EV: { bg: "bg-emerald-50", bar: "bg-emerald-400", glow: "shadow-emerald-400/40", text: "text-emerald-600" },
};

const ZONE_X_PCT: Record<VehicleType, number> = { ICE: 16.67, HYBRID: 50, EV: 83.33 };

interface AggregateSwarmProps {
  tick: Tick;
  prevTick: Tick | null;
}

export default function AggregateSwarm({ tick, prevTick }: AggregateSwarmProps) {
  const { pools, flows, totalConsumers } = useFlowMatrix(
    tick.micro_state,
    prevTick?.micro_state ?? null,
  );

  const step = tick.year;
  const particles = useFlowParticles(flows, step);

  return (
    <div className="relative w-full h-full flex gap-3 p-4">
      {/* Zone pools */}
      {ZONE_ORDER.map((zone) => (
        <ZonePool
          key={zone}
          zone={zone}
          count={pools[zone]}
          total={totalConsumers}
        />
      ))}

      {/* Flying particles overlay */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <AnimatePresence>
          {particles.map((p) => (
            <FlyingParticle key={p.id} particle={p} />
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

// ── Zone Pool ──────────────────────────────────────────────────────

interface ZonePoolProps {
  zone: VehicleType;
  count: number;
  total: number;
}

function ZonePool({ zone, count, total }: ZonePoolProps) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  const colors = ZONE_COLORS[zone];

  return (
    <div className={`flex-1 rounded-2xl ${colors.bg} border border-gray-200 flex flex-col p-4 min-h-0`}>
      {/* Header */}
      <div className="flex items-baseline justify-between mb-3">
        <h3 className={`text-lg font-bold ${colors.text}`}>{zone}</h3>
        <span className="text-sm font-mono text-gray-500">
          {count.toLocaleString()}
        </span>
      </div>

      {/* Vertical fill bar */}
      <div className="flex-1 rounded-xl bg-white/60 relative overflow-hidden min-h-[80px]">
        <motion.div
          className={`absolute bottom-0 left-0 right-0 ${colors.bar} rounded-xl shadow-lg ${colors.glow}`}
          initial={false}
          animate={{ height: `${pct}%` }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
        />
        {/* Percentage label */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-2xl font-bold ${colors.text} drop-shadow-sm`}>
            {pct.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Grid visualization — proportional static dots */}
      <DotGrid count={count} total={total} color={colors.bar} />
    </div>
  );
}

// ── Dot Grid (static, no per-node animation) ──────────────────────

function DotGrid({ count, total, color }: { count: number; total: number; color: string }) {
  // Show a max of 200 representative dots
  const maxDots = 200;
  const dots = Math.round((count / total) * maxDots);

  return (
    <div className="mt-3 flex flex-wrap gap-[3px] justify-center">
      {Array.from({ length: dots }, (_, i) => (
        <div
          key={i}
          className={`w-2 h-2 rounded-full ${color} opacity-70`}
        />
      ))}
    </div>
  );
}

// ── Flying Particle ────────────────────────────────────────────────

function FlyingParticle({ particle }: { particle: FlowParticleData }) {
  const fromX = ZONE_X_PCT[particle.from];
  const toX = ZONE_X_PCT[particle.to];

  const barColor =
    particle.to === "ICE"
      ? "#f87171"
      : particle.to === "HYBRID"
        ? "#60a5fa"
        : "#34d399";

  // Randomize vertical start/end for visual spread
  const yStart = 30 + Math.random() * 40; // 30-70%
  const yEnd = 30 + Math.random() * 40;

  return (
    <motion.div
      className="absolute w-3 h-3 rounded-full"
      style={{ backgroundColor: barColor, boxShadow: `0 0 8px ${barColor}` }}
      initial={{ left: `${fromX}%`, top: `${yStart}%`, opacity: 1, scale: 0.5 }}
      animate={{ left: `${toX}%`, top: `${yEnd}%`, opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0 }}
      transition={{
        duration: 0.7,
        ease: "easeInOut",
      }}
    />
  );
}
