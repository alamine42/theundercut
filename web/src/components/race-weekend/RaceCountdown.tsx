import type { RaceCountdownProps } from "./types";

function formatCountdown(targetDate: string): {
  days: number;
  hours: number;
  minutes: number;
  isImminent: boolean;
  hasStarted: boolean;
} {
  const target = new Date(targetDate);
  const now = new Date();
  const diffMs = target.getTime() - now.getTime();

  if (diffMs <= 0) {
    return { days: 0, hours: 0, minutes: 0, isImminent: true, hasStarted: true };
  }

  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
  const isImminent = diffMs < 24 * 60 * 60 * 1000; // Less than 24 hours

  return { days, hours, minutes, isImminent, hasStarted: false };
}

function formatDateTime(dateStr: string): { date: string; time: string } {
  const date = new Date(dateStr);
  const dateFormatted = date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const timeFormatted = date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
  return { date: dateFormatted, time: timeFormatted };
}

function CountdownUnit({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="countdown-value text-3xl sm:text-4xl md:text-5xl font-bold">
        {String(value).padStart(2, "0")}
      </span>
      <span className="text-[10px] sm:text-xs uppercase tracking-wider text-paper/60 mt-1">
        {label}
      </span>
    </div>
  );
}

export function RaceCountdown({ targetDate, sessionType, label }: RaceCountdownProps) {
  const countdown = formatCountdown(targetDate);
  const { date, time } = formatDateTime(targetDate);

  const displayLabel = label || (sessionType
    ? `${sessionType.replace(/_/g, " ").toUpperCase()} STARTS IN`
    : "RACE STARTS IN");

  if (countdown.hasStarted) {
    return (
      <div className="countdown-container p-4 sm:p-6 text-center animate-fadeInUp">
        <p className="text-xs uppercase tracking-wider text-paper/60 mb-2">
          {sessionType ? sessionType.replace(/_/g, " ").toUpperCase() : "SESSION"}
        </p>
        <div className="status-live inline-flex text-sm">
          In Progress
        </div>
      </div>
    );
  }

  return (
    <div
      className={`countdown-container p-4 sm:p-6 md:p-8 text-center animate-fadeInUp ${
        countdown.isImminent ? "animate-countdownPulse" : ""
      }`}
      role="timer"
      aria-live="polite"
      aria-label={`${displayLabel}: ${countdown.days} days, ${countdown.hours} hours, ${countdown.minutes} minutes`}
    >
      <p className="text-[10px] sm:text-xs uppercase tracking-widest text-paper/50 mb-3 sm:mb-4">
        {displayLabel}
      </p>

      <div className="flex items-center justify-center gap-3 sm:gap-6 md:gap-8">
        {countdown.days > 0 && (
          <>
            <CountdownUnit value={countdown.days} label="days" />
            <span className="text-2xl sm:text-3xl md:text-4xl text-paper/30 font-light">:</span>
          </>
        )}
        <CountdownUnit value={countdown.hours} label="hours" />
        <span className="text-2xl sm:text-3xl md:text-4xl text-paper/30 font-light">:</span>
        <CountdownUnit value={countdown.minutes} label="min" />
      </div>

      <div className="mt-4 sm:mt-5 flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-2 text-paper/60">
        <span className="text-xs sm:text-sm" suppressHydrationWarning>{date}</span>
        <span className="hidden sm:inline text-paper/30">·</span>
        <span className="text-xs sm:text-sm" suppressHydrationWarning>{time}</span>
      </div>

      {/* Progress bar showing time remaining (visual indicator) */}
      {countdown.days <= 7 && (
        <div className="mt-4 sm:mt-5 mx-auto max-w-xs">
          <div className="h-1 bg-paper/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-accent transition-all duration-1000 rounded-full"
              style={{
                width: `${Math.max(5, 100 - (countdown.days * 14 + countdown.hours * 0.6))}%`
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
