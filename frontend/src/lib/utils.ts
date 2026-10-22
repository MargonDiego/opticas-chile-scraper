import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * tailwind-merge does not know about this project's custom font-size tokens
 * (`text-display`, `text-label`, `text-price`, …). Without this registration it
 * classifies them as text *colours* and silently drops them whenever a
 * `text-<colour>` class sits in the same `cn()` call — e.g.
 * `cn("text-label", "text-accent-foreground")` would lose the type size.
 */
const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      text: [
        "display",
        "headline",
        "title",
        "body",
        "body-sm",
        "label",
        "price",
        "price-lg",
      ],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCLP(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return "Consultar";
  return `$${amount.toLocaleString("es-CL")} CLP`;
}

/**
 * Shared focus treatment for every interactive primitive.
 * A 2px petrol ring at 2px offset, visible against both the control and
 * the canvas.
 */
export const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background";

/**
 * Touch geometry: 44px on coarse pointers, 40px when a precise pointer is
 * available.
 */
export const touchTarget = "min-h-11 pointer-fine:min-h-10";

/** Tabular figures so price columns align and a discount reads as a subtraction. */
export const tabularNums = "tabular-nums";

/** Line clamps, spelled out so the class names stay statically analysable. */
export const lineClamp = {
  one: "line-clamp-1",
  two: "line-clamp-2",
  three: "line-clamp-3",
} as const;
