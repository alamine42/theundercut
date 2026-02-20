"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { DEFAULT_SEASON } from "@/lib/constants";

const navLinks = [
  { href: "/", label: "Home" },
  { href: `/standings/${DEFAULT_SEASON}`, label: "Standings" },
  { href: `/analytics/${DEFAULT_SEASON}/1`, label: "Analytics" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="border-b-2 border-ink bg-paper">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <Link href="/" className="font-serif text-xl font-bold tracking-tight">
            THE UNDERCUT
          </Link>

          <nav className="hidden md:flex md:items-center md:gap-6">
            {navLinks.map((link) => {
              const isActive =
                link.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(link.href.split("/").slice(0, 2).join("/"));

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "text-sm font-medium transition-colors",
                    isActive
                      ? "text-accent"
                      : "text-muted hover:text-ink"
                  )}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          <button
            className="md:hidden p-2 -mr-2"
            aria-label="Toggle menu"
            onClick={() => {
              // Mobile menu toggle - could be enhanced with state
            }}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}
