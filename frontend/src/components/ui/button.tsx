import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn, focusRing } from "@/lib/utils";

export const buttonVariants = cva(
  cn(
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-semibold transition-colors duration-fast ease-out",
    focusRing,
    "disabled:pointer-events-none disabled:opacity-50"
  ),
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground hover:bg-primary-hover active:bg-primary-active",
        secondary:
          "border border-border bg-card text-foreground hover:border-border-strong",
        outline:
          "border border-border bg-transparent text-foreground hover:border-border-strong",
        ghost:
          "bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground",
        subtle: "bg-accent text-accent-foreground hover:bg-accent-hover",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive-hover active:bg-destructive-active",
        link: "bg-transparent text-primary underline-offset-4 hover:underline",
      },
      size: {
        sm: "min-h-9 px-3 text-xs pointer-coarse:min-h-11",
        default: "min-h-11 px-[18px] text-sm pointer-fine:min-h-10",
        lg: "min-h-11 px-5 text-sm",
        icon: "h-10 w-10 pointer-coarse:h-11 pointer-coarse:w-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type = "button", ...props }, ref) => {
    return (
      <button
        ref={ref}
        type={type}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
