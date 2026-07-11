export function ScoreDisplay({ score, compact = false, label = "Overall score" }: { score: number; compact?: boolean; label?: string }) {
  if (compact) {
    return (
      <span className="inline-flex items-baseline gap-1 font-mono text-lg font-bold tabular-nums text-ink" aria-label={`${label}: ${score} out of 100`}>
        {score}<span className="text-xs font-medium text-slate-400">/100</span>
      </span>
    );
  }

  return (
    <div className="flex h-28 w-28 shrink-0 flex-col items-center justify-center rounded-full border-[7px] border-mint bg-white shadow-sm" aria-label={`${label}: ${score} out of 100`}>
      <span className="font-mono text-4xl font-bold tracking-tight text-ink">{score}</span>
      <span className="mt-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">of 100</span>
    </div>
  );
}
