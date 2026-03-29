import { memo } from "react";
import { motion } from "framer-motion";

const VEHICLE_COLOR: Record<string, string> = {
  ICE: "#f87171",    // rose-400
  HYBRID: "#60a5fa", // blue-400
  EV: "#34d399",     // emerald-400
};

const GLOW_COLOR: Record<string, string> = {
  ICE: "rgba(248,113,113,0.6)",
  HYBRID: "rgba(96,165,250,0.6)",
  EV: "rgba(52,211,153,0.6)",
};

interface ConsumerDotProps {
  x: number;
  y: number;
  vehicle: string;
  justBought: boolean;
}

const ConsumerDot = memo(function ConsumerDot({
  x,
  y,
  vehicle,
  justBought,
}: ConsumerDotProps) {
  const fill = VEHICLE_COLOR[vehicle] ?? "#9ca3af";

  return (
    <>
      <motion.circle
        cx={x}
        cy={y}
        r={4}
        fill={fill}
        animate={{ cx: x, cy: y }}
        transition={{ type: "spring", stiffness: 80, damping: 15 }}
      />
      {justBought && (
        <motion.circle
          cx={x}
          cy={y}
          fill="none"
          stroke={GLOW_COLOR[vehicle] ?? "rgba(156,163,175,0.5)"}
          strokeWidth={2}
          animate={{ cx: x, cy: y, r: [5, 10, 5], opacity: [1, 0.3, 1] }}
          transition={{
            cx: { type: "spring", stiffness: 80, damping: 15 },
            cy: { type: "spring", stiffness: 80, damping: 15 },
            r: { duration: 0.8, repeat: 2, ease: "easeInOut" },
            opacity: { duration: 0.8, repeat: 2, ease: "easeInOut" },
          }}
        />
      )}
    </>
  );
});

export default ConsumerDot;
