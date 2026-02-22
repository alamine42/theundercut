"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { DEFAULT_SEASON } from "@/lib/constants";

const navLinks = [
  { href: "/", label: "Home" },
  { href: `/standings/${DEFAULT_SEASON}`, label: "Standings" },
  { href: "/circuits", label: "Circuits" },
  { href: `/analytics/${DEFAULT_SEASON}/1`, label: "Analytics" },
];

export function Nav() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="border-b-2 border-ink bg-paper">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-serif text-xl font-bold tracking-tight">
            <Image
              src="/logo.svg"
              alt="The Undercut logo"
              width={28}
              height={28}
              className="flex-shrink-0"
            />
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
            aria-expanded={mobileMenuOpen}
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
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
              {mobileMenuOpen ? (
                <>
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </>
              ) : (
                <>
                  <line x1="3" y1="12" x2="21" y2="12" />
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="18" x2="21" y2="18" />
                </>
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <nav className="border-t border-border-light md:hidden">
          <div className="mx-auto max-w-6xl px-4 py-3 space-y-1">
            {navLinks.map((link) => {
              const isActive =
                link.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(link.href.split("/").slice(0, 2).join("/"));

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    "block py-3 px-2 text-sm font-medium transition-colors",
                    isActive
                      ? "text-accent"
                      : "text-muted hover:text-ink"
                  )}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </header>
  );
}
