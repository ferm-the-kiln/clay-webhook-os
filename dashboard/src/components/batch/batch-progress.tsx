"use client";

export function BatchProgress({
  total,
  completed,
  failed,
}: {
  total: number;
  completed: number;
  failed: number;
}) {
  const done = completed + failed;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-zinc-300">
          {done} / {total} rows processed
        </span>
        <span className="text-sm font-mono text-zinc-400">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-zinc-800 overflow-hidden">
        <div
          className="h-full rounded-full bg-teal-500 transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex gap-4 mt-2 text-xs text-zinc-500">
        <span>Completed: <span className="text-green-400">{completed}</span></span>
        <span>Failed: <span className="text-red-400">{failed}</span></span>
        <span>Queued: <span className="text-zinc-400">{total - done}</span></span>
      </div>
    </div>
  );
}
