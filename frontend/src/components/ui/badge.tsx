import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn, focusRing } from "@/lib/utils";

export const badgeVariants = cva(
  cn(
    "inline-flex items-center gap-1 rounded-sm px-2 py-1 text-xs font-semibold transition-colors duration-fast ease-out",
    focusRing
  ),
  {
    variants: {
      variant: {
        default: "bg-muted text-muted-foreground",
        secondary: "bg-muted text-muted-foreground",
        outline: "border border-border bg-card text-foreground",
        savings: "bg-success-tint text-success-foreground",
        warning: "bg-warning-tint text-warning-foreground",
        destructive: "bg-destructive text-destructive-foreground",
        primary: "bg-accent text-accent-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
Badge.displayName = "Badge";
