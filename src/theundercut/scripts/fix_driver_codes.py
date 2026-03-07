#!/usr/bin/env python3
"""Fix driver codes in session classifications by mapping numeric codes to abbreviations."""
import argparse
import datetime as dt

from theundercut.adapters.db import SessionLocal
from theundercut.models import SessionClassification

# 2026 Driver number to (abbreviation, team, name) mapping from OpenF1
DRIVER_MAP = {
    "1": ("NOR", "McLaren", "Lando NORRIS"),
    "3": ("VER", "Red Bull Racing", "Max VERSTAPPEN"),
    "5": ("BOR", "Audi", "Gabriel BORTOLETO"),
    "6": ("HAD", "Red Bull Racing", "Isack HADJAR"),
    "10": ("GAS", "Alpine", "Pierre GASLY"),
    "11": ("PER", "Cadillac", "Sergio PEREZ"),
    "12": ("ANT", "Mercedes", "Andrea Kimi ANTONELLI"),
    "14": ("ALO", "Aston Martin", "Fernando ALONSO"),
    "16": ("LEC", "Ferrari", "Charles LECLERC"),
    "18": ("STR", "Aston Martin", "Lance STROLL"),
    "23": ("ALB", "Williams", "Alexander ALBON"),
    "27": ("HUL", "Audi", "Nico HULKENBERG"),
    "30": ("LAW", "Racing Bulls", "Liam LAWSON"),
    "31": ("OCO", "Haas F1 Team", "Esteban OCON"),
    "41": ("LIN", "Racing Bulls", "Arvid LINDBLAD"),
    "43": ("COL", "Alpine", "Franco COLAPINTO"),
    "44": ("HAM", "Ferrari", "Lewis HAMILTON"),
    "55": ("SAI", "Williams", "Carlos SAINZ"),
    "63": ("RUS", "Mercedes", "George RUSSELL"),
    "77": ("BOT", "Cadillac", "Valtteri BOTTAS"),
    "81": ("PIA", "McLaren", "Oscar PIASTRI"),
    "87": ("BEA", "Haas F1 Team", "Ollie BEARMAN"),
}


def fix_session(season: int, rnd: int, session_type: str, debug: bool = False):
    """Fix driver codes for a specific session."""
    print(f"Fixing driver codes for {season}-{rnd} {session_type}...", flush=True)

    with SessionLocal() as db:
        rows = db.query(SessionClassification).filter_by(
            season=season, round=rnd, session_type=session_type
        ).all()

        if not rows:
            print(f"  No records found for {season}-{rnd} {session_type}", flush=True)
            return

        print(f"  Found {len(rows)} records", flush=True)

        if debug:
            for row in rows[:3]:
                dc = row.driver_code
                print(f"  DEBUG: P{row.position} driver_code={repr(dc)} in_map={dc in DRIVER_MAP}", flush=True)

        updated = 0
        for row in rows:
            if row.driver_code in DRIVER_MAP:
                abbr, team, name = DRIVER_MAP[row.driver_code]
                row.driver_code = abbr
                row.team = team
                row.driver_name = name
                row.ingested_at = dt.datetime.now(dt.timezone.utc)
                updated += 1
                print(f"  Updated P{row.position}: {abbr} ({team})", flush=True)

        db.commit()
        print(f"  Updated {updated} of {len(rows)} records", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Fix driver codes in session results")
    parser.add_argument("--season", type=int, required=True, help="Season year")
    parser.add_argument("--round", type=int, required=True, help="Round number")
    parser.add_argument("--session", type=str, required=True, help="Session type (e.g., qualifying)")
    parser.add_argument("--debug", action="store_true", help="Print debug info")
    args = parser.parse_args()

    fix_session(args.season, args.round, args.session, debug=args.debug)
    print("Done!", flush=True)


if __name__ == "__main__":
    main()
