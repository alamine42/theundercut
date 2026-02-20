import Link from "next/link";

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t-2 border-ink bg-paper">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
          <div className="flex flex-col items-center gap-2 md:flex-row md:gap-4">
            <span className="font-serif font-bold">THE UNDERCUT</span>
            <span className="text-xs text-muted">
              F1 Analytics Dashboard
            </span>
          </div>

          <nav className="flex items-center gap-6 text-xs">
            <Link href="/privacy" className="text-muted hover:text-ink transition-colors">
              Privacy
            </Link>
            <Link href="/terms" className="text-muted hover:text-ink transition-colors">
              Terms
            </Link>
          </nav>
        </div>

        <div className="mt-6 text-center text-xs text-muted">
          <p>
            {currentYear} The Undercut. Not affiliated with Formula 1 or FIA.
          </p>
          <p className="mt-1">
            Data sourced from FastF1 and OpenF1.
          </p>
        </div>
      </div>
    </footer>
  );
}
