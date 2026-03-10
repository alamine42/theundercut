"use client";

import { cn } from "@/lib/utils";

interface ScoreIndicatorProps {
  score: number | null;
  label?: string | null;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

function getScoreColor(score: number): string {
  if (score <= 3) return "bg-emerald-500";
  if (score <= 5) return "bg-amber-400";
  if (score <= 7) return "bg-orange-500";
  return "bg-red-500";
}

function getScoreIcon(score: number): string {
  if (score <= 3) return "Low";
  if (score <= 5) return "Med";
  if (score <= 7) return "High";
  return "V.High";
}

function getScoreTextColor(score: number): string {
  if (score <= 3) return "text-emerald-700";
  if (score <= 5) return "text-amber-700";
  if (score <= 7) return "text-orange-700";
  return "text-red-700";
}

export function ScoreIndicator({
  score,
  label,
  showLabel = false,
  size = "md",
  className,
}: ScoreIndicatorProps) {
  if (score === null) {
    return (
      <span className={cn("text-muted", className)}>
        --
      </span>
    );
  }

  const sizeClasses = {
    sm: "h-1.5 w-12",
    md: "h-2 w-16",
    lg: "h-2.5 w-20",
  };

  const textSizeClasses = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base",
  };

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* Score bar */}
      <div className={cn("relative rounded-full bg-gray-200", sizeClasses[size])}>
        <div
          className={cn("absolute left-0 top-0 h-full rounded-full transition-all", getScoreColor(score))}
          style={{ width: `${score * 10}%` }}
          role="progressbar"
          aria-valuenow={score}
          aria-valuemin={1}
          aria-valuemax={10}
        />
      </div>

      {/* Numeric score */}
      <span className={cn("font-mono font-medium tabular-nums", textSizeClasses[size], getScoreTextColor(score))}>
        {score}
      </span>

      {/* Accessible text indicator */}
      <span className={cn("text-xs uppercase tracking-wide", getScoreTextColor(score))}>
        {showLabel && label ? label : getScoreIcon(score)}
      </span>
    </div>
  );
}

// Compact score badge for tables
interface ScoreBadgeProps {
  score: number | null;
  className?: string;
}

export function ScoreBadge({ score, className }: ScoreBadgeProps) {
  if (score === null) {
    return <span className={cn("text-muted text-sm", className)}>--</span>;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium rounded-full",
        score <= 3 && "bg-emerald-100 text-emerald-800",
        score > 3 && score <= 5 && "bg-amber-100 text-amber-800",
        score > 5 && score <= 7 && "bg-orange-100 text-orange-800",
        score > 7 && "bg-red-100 text-red-800",
        className
      )}
    >
      {score}/10
    </span>
  );
}
