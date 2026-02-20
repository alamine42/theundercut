"use client";

import { cn } from "@/lib/utils";
import { HTMLAttributes, forwardRef } from "react";

export interface ChartContainerProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  description?: string;
  height?: number;
}

const ChartContainer = forwardRef<HTMLDivElement, ChartContainerProps>(
  ({ className, title, description, height = 400, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("border-2 border-ink bg-paper p-4", className)}
        {...props}
      >
        {(title || description) && (
          <div className="mb-4">
            {title && (
              <h3 className="font-semibold tracking-tight">{title}</h3>
            )}
            {description && (
              <p className="text-xs text-muted mt-1">{description}</p>
            )}
          </div>
        )}
        <div style={{ height }}>{children}</div>
      </div>
    );
  }
);

ChartContainer.displayName = "ChartContainer";

export { ChartContainer };
