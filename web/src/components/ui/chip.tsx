"use client";

import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";

export interface ChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
  color?: string;
}

const Chip = forwardRef<HTMLButtonElement, ChipProps>(
  ({ className, active = false, color, style, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center",
          "h-8 px-3 text-xs font-medium",
          "border-2 border-ink transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink",
          active
            ? "bg-accent text-paper border-accent"
            : "bg-paper text-ink hover:bg-ink hover:text-paper",
          className
        )}
        style={{
          ...style,
          ...(color && active
            ? { backgroundColor: color, borderColor: color }
            : {}),
        }}
        {...props}
      />
    );
  }
);

Chip.displayName = "Chip";

export { Chip };
