import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          // 44px on touch, 40px with a precise pointer. 16px base text keeps
          // iOS from zooming the viewport on focus; 15px once a pointer exists.
          "h-11 min-h-11 w-full pointer-fine:h-10 pointer-fine:min-h-10",
          "rounded-md border border-input bg-card px-3 text-[16px] pointer-fine:text-[15px]",
          "file:border-0 file:bg-transparent file:text-sm file:font-medium",
          "placeholder:text-muted-foreground",
          "transition-colors duration-fast ease-out",
          // The global 2px petrol outline is the focus indicator; the solid
          // petrol border is the second half of it.
          "focus-visible:border-primary",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";
