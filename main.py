#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from datetime import datetime
from collections import defaultdict

import calassist

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APPLESCRIPT_PATH = os.path.join(SCRIPT_DIR, "calassist.applescript")


def run_applescript(*args):
    result = subprocess.run(
        ["osascript", APPLESCRIPT_PATH] + [str(a) for a in args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
    return result.returncode == 0, (result.stdout or "").strip(), (result.stderr or "").strip()


def _day_sort_key(day_label):
    """Sort key: 'Other' last; others by parsed date for chronological order."""
    if day_label == "Other":
        return (1, datetime.max)
    try:
        dt = datetime.strptime(day_label, "%A, %B %d")
        return (0, dt)
    except ValueError:
        return (0, datetime.min)


def pretty_print_list_week(raw_output):
    """Parse 'title | date' lines and group by day with readable formatting."""
    if not raw_output:
        print("No events this week.")
        return
    by_day = defaultdict(list)
    for line in raw_output.splitlines():
        line = line.strip()
        if " | " not in line:
            continue
        title, date_str = line.split(" | ", 1)
        title, date_str = title.strip(), date_str.strip()
        try:
            # AppleScript date format is often like "Thursday, March 13, 2025 at 2:00:00 PM"
            part = date_str.split(" at ")[0].strip()
            dt = datetime.strptime(part, "%A, %B %d, %Y")
            time_part = date_str.split(" at ")[1].strip() if " at " in date_str else ""
            day_key = dt.strftime("%A, %B %d")
            by_day[day_key].append((title, time_part, date_str))
        except Exception:
            by_day["Other"].append((title, "", date_str))
    for day in sorted(by_day.keys(), key=_day_sort_key):
        print(f"\n  {day}")
        print("  " + "-" * 40)
        for title, time_part, full in by_day[day]:
            if time_part:
                print(f"    • {title}  —  {time_part}")
            else:
                print(f"    • {title}  —  {full}")


def main():
    parser = argparse.ArgumentParser(description="AI Calendar Assistant")
    parser.add_argument("text", nargs="+", help="Natural language command (e.g. add meeting tomorrow 12-1)")
    parser.add_argument("--calendar", "-c", default="Calendar", help="Calendar name (default: Calendar)")
    parser.add_argument("--no-conflict-check", action="store_true", help="Skip conflict check when adding events")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without making changes")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation for delete")
    parser.add_argument("--duration", "-d", type=int, default=None, help="Default event duration in minutes when no time given")
    args = parser.parse_args()

    user_input = " ".join(args.text)

    try:
        parsed = calassist.parse_command(
            user_input,
            default_calendar=args.calendar,
            default_duration_minutes=args.duration or calassist.DEFAULT_DURATION_MINUTES,
        )
    except ValueError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)

    intent = parsed["intent"]
    calendar = parsed.get("calendar") or args.calendar

    if intent == "unknown":
        print("Could not understand command. Try: add ..., delete ..., modify ... to ..., what do i have, remind me to ...", file=sys.stderr)
        sys.exit(1)

    # ---------------------------
    # Dry run: show and exit
    # ---------------------------
    if args.dry_run:
        print("Dry run — would execute:")
        print(f"  Intent: {intent}")
        print(f"  Parsed: {parsed}")
        if intent == "add":
            print(f"  Add event '{parsed['title']}' on {parsed['start']} - {parsed['end']} (calendar: {calendar})")
        elif intent == "delete":
            print(f"  Delete events titled '{parsed['title']}' from {calendar}")
        elif intent == "modify":
            print(f"  Modify '{parsed['title']}' to {parsed['start']} - {parsed['end']} in {calendar}")
        elif intent == "list_week":
            print(f"  List week for calendar: {calendar}")
        elif intent == "remind":
            print(f"  Add reminder '{parsed['title']}'" + (f" due {parsed['start']}" if parsed.get("start") else ""))
        return

    # ---------------------------
    # ADD
    # ---------------------------
    if intent == "add":
        if not args.no_conflict_check:
            ok, out, err = run_applescript(
                "check_conflict",
                calendar,
                parsed["start"].strftime("%m/%d/%Y %I:%M %p"),
                parsed["end"].strftime("%m/%d/%Y %I:%M %p"),
            )
            if ok and out == "CONFLICT":
                print("Conflict: you already have an event in this time range. Use --no-conflict-check to add anyway.", file=sys.stderr)
                sys.exit(1)
        args_list = [
            "add",
            calendar,
            parsed["title"],
            parsed["start"].strftime("%m/%d/%Y %I:%M %p"),
            parsed["end"].strftime("%m/%d/%Y %I:%M %p"),
        ]
        if parsed.get("recurrence"):
            args_list.append(parsed["recurrence"])
        ok, out, err = run_applescript(*args_list)
        if ok:
            print(out)
        else:
            sys.exit(1)
        return

    # ---------------------------
    # DELETE (with optional confirm)
    # ---------------------------
    if intent == "delete":
        if not args.yes:
            try:
                answer = input(f"Delete event(s) '{parsed['title']}'? [y/N] ").strip().lower()
                if answer not in ("y", "yes"):
                    print("Cancelled.")
                    return
            except EOFError:
                print("Cancelled.")
                return
        ok, out, err = run_applescript("delete", calendar, parsed["title"])
        if ok:
            print(out)
        else:
            sys.exit(1)
        return

    # ---------------------------
    # MODIFY
    # ---------------------------
    if intent == "modify":
        ok, out, err = run_applescript(
            "modify",
            calendar,
            parsed["title"],
            parsed["start"].strftime("%m/%d/%Y %I:%M %p"),
            parsed["end"].strftime("%m/%d/%Y %I:%M %p"),
        )
        if ok:
            print(out)
        else:
            sys.exit(1)
        return

    # ---------------------------
    # LIST WEEK (pretty-print)
    # ---------------------------
    if intent == "list_week":
        ok, out, err = run_applescript("list_week", calendar)
        if ok:
            pretty_print_list_week(out)
        else:
            sys.exit(1)
        return

    # ---------------------------
    # REMIND (Reminders app)
    # ---------------------------
    if intent == "remind":
        args_list = ["add_reminder", parsed["title"]]
        if parsed.get("start"):
            # Use format AppleScript date() accepts (same as Calendar for consistency)
            args_list.append(parsed["start"].strftime("%m/%d/%Y %I:%M %p"))
        else:
            args_list.append("")
        ok, out, err = run_applescript(*args_list)
        if ok:
            print(out)
        else:
            sys.exit(1)
        return

    sys.exit(1)


if __name__ == "__main__":
    main()
