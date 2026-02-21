"use client";

import { cn } from "@/lib/utils";
import { HTMLAttributes, forwardRef } from "react";

export interface ChartContainerProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  description?: string;
  height?: number;
  mobileHeight?: number;
}

const ChartContainer = forwardRef<HTMLDivElement, ChartContainerProps>(
  ({ className, title, description, height = 400, mobileHeight, children, ...props }, ref) => {
    const mobile = mobileHeight ?? Math.min(height, 300);
    return (
      <div
        ref={ref}
        className={cn("border-2 border-ink bg-paper p-3 sm:p-4", className)}
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
        <div
          className="chart-height-container"
          style={{ "--chart-height-mobile": `${mobile}px`, "--chart-height": `${height}px` } as React.CSSProperties}
        >
          {children}
        </div>
      </div>
    );
  }
);

ChartContainer.displayName = "ChartContainer";

export { ChartContainer };
