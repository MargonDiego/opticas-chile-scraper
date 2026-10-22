import * as React from "react";
import { cn } from "@/lib/utils";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={cn(
          // 44px on touch, 40px with a precise pointer. 16px base text keeps
          // iOS from zooming the viewport on focus; 15px once a pointer exists.
          "h-11 min-h-11 w-full pointer-fine:h-10 pointer-fine:min-h-10",
          "appearance-none rounded-md border border-input bg-card px-3 pr-9 text-[16px] pointer-fine:text-[15px]",
          // Custom chevron, themed per colour scheme in globals.css.
          "select-chevron",
          "transition-colors duration-fast ease-out",
          // The global 2px petrol outline is the focus indicator; the solid
          // petrol border is the second half of it.
          "focus-visible:border-primary",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        {...props}
      >
        {children}
      </select>
    );
  }
);
Select.displayName = "Select";
