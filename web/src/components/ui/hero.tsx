import { cn } from "@/lib/utils";
import { HTMLAttributes, forwardRef } from "react";

export interface HeroProps extends HTMLAttributes<HTMLElement> {}

const Hero = forwardRef<HTMLElement, HeroProps>(
  ({ className, ...props }, ref) => {
    return (
      <section
        ref={ref}
        className={cn(
          "racing-stripe bg-paper py-12 md:py-16",
          className
        )}
        {...props}
      />
    );
  }
);

Hero.displayName = "Hero";

const HeroTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => {
    return (
      <h1
        ref={ref}
        className={cn(
          "font-serif text-3xl font-bold tracking-tight md:text-4xl lg:text-5xl",
          className
        )}
        {...props}
      />
    );
  }
);

HeroTitle.displayName = "HeroTitle";

const HeroSubtitle = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => {
    return (
      <p
        ref={ref}
        className={cn("mt-2 text-muted", className)}
        {...props}
      />
    );
  }
);

HeroSubtitle.displayName = "HeroSubtitle";

export interface HeroStatProps extends HTMLAttributes<HTMLDivElement> {
  label: string;
  value: string | number;
}

const HeroStat = forwardRef<HTMLDivElement, HeroStatProps>(
  ({ className, label, value, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("text-center md:text-left", className)}
        {...props}
      >
        <div className="text-2xl font-semibold md:text-3xl">{value}</div>
        <div className="text-xs text-muted uppercase tracking-wider">{label}</div>
      </div>
    );
  }
);

HeroStat.displayName = "HeroStat";

const HeroStats = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "mt-8 flex flex-wrap justify-center gap-8 md:justify-start md:gap-12",
          className
        )}
        {...props}
      />
    );
  }
);

HeroStats.displayName = "HeroStats";

export { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats };
