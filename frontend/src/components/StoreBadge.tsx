import React from "react";

interface StoreBadgeProps {
  store: string;
}

/**
 * The chain identity is kept — it tells the reader where a price comes from at a
 * glance — but it is carried by a 6px dot only. The name itself is plain muted
 * text: no pill, no border, no mono, no uppercase, no shadow.
 *
 * The dot colour is the one place a chain is allowed its own hue; the text
 * colour never changes, so the hue can never be the only thing carrying the
 * meaning. The hues live in `globals.css` as `--store-*` tokens, at a mid
 * lightness so one value reads on the light and the dark canvas alike.
 */
const STORE_CONFIG: Record<string, { label: string; dotColor: string }> = {
  gmo: {
    label: "GMO",
    dotColor: "bg-[var(--store-gmo)]",
  },
  place_vendome: {
    label: "Place Vendôme",
    dotColor: "bg-[var(--store-vendome)]",
  },
  ryk: {
    label: "Rotter & Krauss",
    dotColor: "bg-[var(--store-rk)]",
  },
  schilling: {
    label: "Schilling",
    dotColor: "bg-[var(--store-schilling)]",
  },
  econopticas: {
    label: "Econópticas",
    dotColor: "bg-[var(--store-econopticas)]",
  },
  karun: {
    label: "Karün",
    dotColor: "bg-[var(--store-karun)]",
  },
  lentesplus: {
    label: "Lentesplus",
    dotColor: "bg-[var(--store-lentesplus)]",
  },
};

export function StoreBadge({ store }: StoreBadgeProps) {
  const config = STORE_CONFIG[store.toLowerCase()] || {
    label: store,
    dotColor: "bg-[var(--store-unknown)]",
  };

  return (
    <span className="inline-flex min-w-0 items-center gap-1.5 text-body-sm text-muted-foreground">
      <span
        aria-hidden="true"
        className={`h-1.5 w-1.5 shrink-0 rounded-full ${config.dotColor}`}
      />
      <span className="truncate">{config.label}</span>
    </span>
  );
}
