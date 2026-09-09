import React from "react";
import { Badge } from "./ui/badge";

interface StoreBadgeProps {
  store: string;
}

const STORE_CONFIG: Record<string, { label: string; className: string }> = {
  gmo: {
    label: "GMO Chile",
    className: "bg-emerald-600/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
  },
  place_vendome: {
    label: "Place Vendôme",
    className: "bg-purple-600/15 text-purple-700 dark:text-purple-400 border-purple-500/30",
  },
  ryk: {
    label: "Rotter & Krauss",
    className: "bg-blue-600/15 text-blue-700 dark:text-blue-400 border-blue-500/30",
  },
  schilling: {
    label: "Ópticas Schilling",
    className: "bg-indigo-600/15 text-indigo-700 dark:text-indigo-400 border-indigo-500/30",
  },
  econopticas: {
    label: "Econópticas",
    className: "bg-amber-600/15 text-amber-700 dark:text-amber-400 border-amber-500/30",
  },
  karun: {
    label: "Karün Chile",
    className: "bg-teal-600/15 text-teal-700 dark:text-teal-400 border-teal-500/30",
  },
  lentesplus: {
    label: "Lentesplus",
    className: "bg-cyan-600/15 text-cyan-700 dark:text-cyan-400 border-cyan-500/30",
  },
};

export function StoreBadge({ store }: StoreBadgeProps) {
  const config = STORE_CONFIG[store.toLowerCase()] || {
    label: store.toUpperCase(),
    className: "bg-slate-500/15 text-slate-700 border-slate-500/30",
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${config.className}`}>
      {config.label}
    </span>
  );
}