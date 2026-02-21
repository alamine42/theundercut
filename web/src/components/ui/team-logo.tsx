"use client";

import Image from "next/image";
import { getTeamId, TEAM_COLORS } from "@/lib/constants";

interface TeamLogoProps {
  team: string;
  size?: number;
  className?: string;
}

export function TeamLogo({ team, size = 20, className = "" }: TeamLogoProps) {
  const teamId = getTeamId(team);
  const teamColor = TEAM_COLORS[team] || "#888888";

  return (
    <Image
      src={`/teams/${teamId}.svg`}
      alt={`${team} logo`}
      width={size}
      height={size}
      className={`inline-block ${className}`}
      style={{ minWidth: size, minHeight: size }}
      onError={(e) => {
        // Fallback to colored circle if logo not found
        const target = e.currentTarget;
        target.style.display = "none";
        const fallback = target.nextElementSibling as HTMLElement;
        if (fallback) fallback.style.display = "flex";
      }}
    />
  );
}

// Combined component that shows logo + team name
interface TeamWithLogoProps {
  team: string;
  size?: number;
  className?: string;
}

export function TeamWithLogo({ team, size = 16, className = "" }: TeamWithLogoProps) {
  const teamId = getTeamId(team);
  const teamColor = TEAM_COLORS[team] || "#888888";

  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`}>
      <Image
        src={`/teams/${teamId}.svg`}
        alt=""
        width={size}
        height={size}
        className="inline-block flex-shrink-0"
        onError={(e) => {
          // Replace with colored dot on error
          const target = e.currentTarget;
          target.style.display = "none";
          const parent = target.parentElement;
          if (parent) {
            const dot = document.createElement("span");
            dot.className = "inline-block flex-shrink-0 rounded-full";
            dot.style.width = `${size}px`;
            dot.style.height = `${size}px`;
            dot.style.backgroundColor = teamColor;
            parent.insertBefore(dot, target);
          }
        }}
      />
      <span>{team}</span>
    </span>
  );
}
