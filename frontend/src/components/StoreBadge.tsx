import React from "react";

interface StoreBadgeProps {
  store: string;
}

const STORE_CONFIG: Record<string, { label: string; dotColor: string; className: string }> = {
  gmo: {
    label: "GMO",
    dotColor: "bg-emerald-500",
    className: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/25",
  },
  place_vendome: {
    label: "Place Vendôme",
    dotColor: "bg-purple-500",
    className: "bg-purple-500/10 text-purple-600 dark:text-purple-300 border-purple-500/25",
  },
  ryk: {
    label: "Rotter & Krauss",
    dotColor: "bg-blue-500",
    className: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/25",
  },
  schilling: {
    label: "Schilling",
    dotColor: "bg-indigo-500",
    className: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/25",
  },
  econopticas: {
    label: "Econópticas",
    dotColor: "bg-amber-500",
    className: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/25",
  },
  karun: {
    label: "Karün",
    dotColor: "bg-teal-500",
    className: "bg-teal-500/10 text-teal-600 dark:text-teal-400 border-teal-500/25",
  },
  lentesplus: {
    label: "Lentesplus",
    dotColor: "bg-cyan-500",
    className: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/25",
  },
};

export function StoreBadge({ store }: StoreBadgeProps) {
  const config = STORE_CONFIG[store.toLowerCase()] || {
    label: store.toUpperCase(),
    dotColor: "bg-slate-400",
    className: "bg-muted/60 text-muted-foreground border-border/80",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-mono text-[10px] font-bold uppercase tracking-wider border shadow-xs transition-colors ${config.className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor}`} />
      <span>{config.label}</span>
    </span>
  );
}