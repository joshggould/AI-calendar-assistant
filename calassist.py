import spacy
from dateparser import parse as dateparser_parse
from dateparser.search import search_dates
from datetime import datetime, timedelta
import re

nlp = spacy.load("en_core_web_sm")

# Default event duration when no time range is given (minutes)
DEFAULT_DURATION_MINUTES = 30

# Words to strip when extracting title (intent + date/time related)
INTENT_PREFIXES = ("add", "delete", "modify", "remind me to")
DATE_WORDS = ("today", "tomorrow", "noon", "afternoon", "morning", "evening")
RECURRENCE_DAYS = {"monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH", "friday": "FR", "saturday": "SA", "sunday": "SU"}


def _extract_title_spacy(text):
    """Use spaCy to extract event title (noun chunks and key phrases)."""
    text = text.strip()
    if not text:
        return ""
    doc = nlp(text)
    # Prefer noun chunks; fallback to full text cleaned
    chunks = [c.text.strip() for c in doc.noun_chunks if c.text.strip()]
    if chunks:
        return " ".join(chunks).title()
    return text.title()


def _parse_time_range(user_input):
    """Extract start/end hour from patterns like 12-1, 2-3, 2pm-3pm."""
    # e.g. 12-1, 2-3
    m = re.search(r"(\d{1,2})-(\d{1,2})\s*(?:pm|am|AM|PM)?", user_input, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    # e.g. 2pm to 3pm, 2 pm - 3 pm
    m = re.search(r"(\d{1,2})\s*(?:pm|am|AM|PM)?\s*(?:to|-)\s*(\d{1,2})\s*(?:pm|am|AM|PM)?", user_input, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def _parse_date_from_string(user_input):
    """Parse date from natural language (today, tomorrow, noon, in 2 hours, next Monday 3pm, etc.)."""
    # Try full string first (e.g. "tomorrow at noon", "in 2 hours")
    dt = dateparser_parse(user_input, settings={"PREFER_DATES_FROM": "future"})
    if dt:
        return dt
    results = search_dates(user_input, settings={"PREFER_DATES_FROM": "future"})
    if results:
        return results[0][1]
    if "tomorrow" in user_input:
        return datetime.now() + timedelta(days=1)
    if "today" in user_input:
        return datetime.now()
    if "noon" in user_input or "12 pm" in user_input:
        base = datetime.now()
        if "tomorrow" in user_input:
            base += timedelta(days=1)
        return base.replace(hour=12, minute=0, second=0, microsecond=0)
    if "afternoon" in user_input:
        base = datetime.now()
        if "tomorrow" in user_input:
            base += timedelta(days=1)
        return base.replace(hour=14, minute=0, second=0, microsecond=0)
    if "morning" in user_input:
        base = datetime.now()
        if "tomorrow" in user_input:
            base += timedelta(days=1)
        return base.replace(hour=9, minute=0, second=0, microsecond=0)
    if "evening" in user_input:
        base = datetime.now()
        if "tomorrow" in user_input:
            base += timedelta(days=1)
        return base.replace(hour=18, minute=0, second=0, microsecond=0)
    return None


def _parse_recurrence(user_input):
    """Detect 'every Monday' / 'every Tuesday 2-3' and return iCal FREQ line or None."""
    low = user_input.lower()
    for day_name, byday in RECURRENCE_DAYS.items():
        if f"every {day_name}" in low:
            return f"FREQ=WEEKLY;BYDAY={byday}"
    return None


def _title_cleaned_for_add(original_input, intent_prefix, time_range_str_removed):
    """Remove intent, date words, time range, recurrence words to get title fragment for add."""
    cleaned = original_input.lower()
    for p in INTENT_PREFIXES:
        if cleaned.startswith(p):
            cleaned = cleaned[len(p):].strip()
            break
    cleaned = re.sub(r"\d{1,2}-\d{1,2}\s*(?:pm|am)?", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\d{1,2}\s*(?:pm|am)?\s*(?:to|-)\s*\d{1,2}\s*(?:pm|am)?", "", cleaned, flags=re.I)
    for w in DATE_WORDS:
        cleaned = cleaned.replace(w, "")
    cleaned = re.sub(r"\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bin\s+\d+\s+(hour|hours|minute|minutes|day|days)\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\b(at|on)\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def parse_command(user_input, default_calendar="Calendar", default_duration_minutes=None):
    if default_duration_minutes is None:
        default_duration_minutes = DEFAULT_DURATION_MINUTES

    original_input = user_input
    user_input_lower = user_input.lower()

    # -----------------------
    # 1) Detect Intent
    # -----------------------
    if user_input_lower.startswith("add"):
        intent = "add"
    elif user_input_lower.startswith("delete"):
        intent = "delete"
    elif user_input_lower.startswith("modify"):
        intent = "modify"
    elif "what do i have" in user_input_lower or user_input_lower.startswith("list week"):
        intent = "list_week"
    elif user_input_lower.startswith("remind me to"):
        intent = "remind"
    else:
        intent = "unknown"

    result = {"intent": intent, "title": "", "start": None, "end": None, "calendar": default_calendar, "recurrence": None}

    # -----------------------
    # Delete: only need title
    # -----------------------
    if intent == "delete":
        title_part = user_input_lower.replace("delete", "", 1).strip()
        result["title"] = _extract_title_spacy(title_part) if title_part else title_part.title()
        return result

    # -----------------------
    # List week: nothing else
    # -----------------------
    if intent == "list_week":
        return result

    # -----------------------
    # Remind: title (+ optional when)
    # -----------------------
    if intent == "remind":
        title_part = user_input_lower.replace("remind me to", "", 1).strip()
        result["title"] = title_part.title() if title_part else "Reminder"
        # Only set due date if user included clear date/time words (avoid spurious parses)
        date_keywords = ("tomorrow", "today", "next", "tonight", "noon", "morning", "afternoon", "evening", "at ", "on monday", "on tuesday", "on wednesday", "on thursday", "on friday", "on saturday", "on sunday")
        if any(k in user_input_lower for k in date_keywords):
            when = _parse_date_from_string(original_input)
            if when:
                result["start"] = when
                result["end"] = when + timedelta(minutes=1)
        return result

    # -----------------------
    # Modify: "modify <title> to <new time>"
    # -----------------------
    if intent == "modify":
        to_match = re.search(r"\bto\b", user_input_lower)
        if to_match:
            before_to = user_input_lower[: to_match.start()].replace("modify", "", 1).strip()
            after_to = original_input[to_match.end():].strip()
            result["title"] = _extract_title_spacy(before_to) if before_to else before_to.title()
            parsed_date = _parse_date_from_string(after_to)
            if not parsed_date:
                raise ValueError("Could not detect new date/time for modify.")
            start_hour, end_hour = _parse_time_range(after_to)
            if start_hour is not None and end_hour is not None:
                if end_hour <= start_hour and end_hour < 12:
                    end_hour = end_hour + 12
                start_date = parsed_date.replace(hour=start_hour % 24, minute=0, second=0, microsecond=0)
                end_date = parsed_date.replace(hour=end_hour % 24, minute=0, second=0, microsecond=0)
            else:
                start_date = parsed_date
                end_date = start_date + timedelta(minutes=default_duration_minutes)
            result["start"] = start_date
            result["end"] = end_date
        else:
            raise ValueError("Modify format: modify <title> to <new time>")
        return result

    # -----------------------
    # Add: time range, date, recurrence, title (spaCy)
    # -----------------------
    if intent == "add":
        start_hour, end_hour = _parse_time_range(user_input_lower)
        recurrence = _parse_recurrence(user_input_lower)

        # Build text with time range removed for date parsing
        input_for_date = re.sub(r"\d{1,2}-\d{1,2}\s*(?:pm|am)?", "", user_input_lower, flags=re.I)
        input_for_date = re.sub(r"\d{1,2}\s*(?:pm|am)?\s*(?:to|-)\s*\d{1,2}\s*(?:pm|am)?", "", input_for_date, flags=re.I)
        parsed_date = _parse_date_from_string(input_for_date or user_input_lower)
        if not parsed_date:
            raise ValueError("Could not detect date.")

        if start_hour is not None and end_hour is not None:
            # e.g. 12-1 means noon to 1pm: if end <= start, assume end is PM
            if end_hour <= start_hour and end_hour < 12:
                end_hour = end_hour + 12
            start_date = parsed_date.replace(hour=start_hour % 24, minute=0, second=0, microsecond=0)
            end_date = parsed_date.replace(hour=end_hour % 24, minute=0, second=0, microsecond=0)
        else:
            start_date = parsed_date
            end_date = start_date + timedelta(minutes=default_duration_minutes)

        title_fragment = _title_cleaned_for_add(original_input, "add", None)
        result["title"] = _extract_title_spacy(title_fragment) if title_fragment else "Event"
        result["start"] = start_date
        result["end"] = end_date
        result["recurrence"] = recurrence
        return result

    return result
