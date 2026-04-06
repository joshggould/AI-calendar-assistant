import spacy
from dateparser import parse as dateparser_parse
from dateparser.search import search_dates
from datetime import datetime, timedelta
import re

nlp = spacy.load("en_core_web_sm")

DEFAULT_DURATION_MINUTES = 30
INTENT_PREFIXES = ("add", "delete", "modify", "remind me to")
DATE_WORDS = ("today", "tomorrow", "noon", "afternoon", "morning", "evening")
RECURRENCE_DAYS = {
    "monday": "MO",
    "tuesday": "TU",
    "wednesday": "WE",
    "thursday": "TH",
    "friday": "FR",
    "saturday": "SA",
    "sunday": "SU",
}


def _extract_title_spacy(text):
    text = text.strip()
    if not text:
        return ""
    doc = nlp(text)
    chunks = [c.text.strip() for c in doc.noun_chunks if c.text.strip()]
    if chunks:
        return " ".join(chunks).title()
    return text.title()


def _parse_time_range(user_input):
    user_input = user_input.lower()

    patterns = [
        r"(\d{1,2}):(\d{2})\s*(am|pm)\s*(?:to|-)\s*(\d{1,2}):(\d{2})\s*(am|pm)",
        r"(\d{1,2})\s*(am|pm)\s*(?:to|-)\s*(\d{1,2})\s*(am|pm)",
        r"(\d{1,2}):(\d{2})\s*(?:to|-)\s*(\d{1,2}):(\d{2})\s*(am|pm)",
        r"(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\s*(am|pm)",
    ]

    m = re.search(patterns[0], user_input, re.I)
    if m:
        sh, sm, sap, eh, em, eap = m.groups()
        return (int(sh), int(sm), sap.lower(), int(eh), int(em), eap.lower())

    m = re.search(patterns[1], user_input, re.I)
    if m:
        sh, sap, eh, eap = m.groups()
        return (int(sh), 0, sap.lower(), int(eh), 0, eap.lower())

    m = re.search(patterns[2], user_input, re.I)
    if m:
        sh, sm, eh, em, ap = m.groups()
        ap = ap.lower()
        return (int(sh), int(sm), ap, int(eh), int(em), ap)

    m = re.search(patterns[3], user_input, re.I)
    if m:
        sh, eh, ap = m.groups()
        ap = ap.lower()
        return (int(sh), 0, ap, int(eh), 0, ap)

    return None


def _to_24h(hour, minute, ampm):
    hour = int(hour)
    minute = int(minute)
    ampm = ampm.lower()

    if ampm == "am":
        if hour == 12:
            hour = 0
    elif ampm == "pm":
        if hour != 12:
            hour += 12

    return hour, minute


def _parse_date_from_string(user_input):
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
    if "noon" in user_input:
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
    low = user_input.lower()

    count = None
    count_match = re.search(r"for\s+(\d+)\s+weeks?", low)
    if count_match:
        count = int(count_match.group(1))

    for day_name, byday in RECURRENCE_DAYS.items():
        if f"every other {day_name}" in low or f"every other week on {day_name}" in low:
            rule = f"FREQ=WEEKLY;INTERVAL=2;BYDAY={byday}"
            if count:
                rule += f";COUNT={count}"
            return rule

        if f"biweekly {day_name}" in low:
            rule = f"FREQ=WEEKLY;INTERVAL=2;BYDAY={byday}"
            if count:
                rule += f";COUNT={count}"
            return rule

        if f"every {day_name}" in low:
            rule = f"FREQ=WEEKLY;BYDAY={byday}"
            if count:
                rule += f";COUNT={count}"
            return rule

    return None


def _title_cleaned_for_add(original_input):
    cleaned = original_input.lower()

    for p in INTENT_PREFIXES:
        if cleaned.startswith(p):
            cleaned = cleaned[len(p):].strip()
            break

    cleaned = re.sub(r"for\s+\d+\s+weeks?", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\d{1,2}:\d{2}\s*(am|pm)\s*(?:to|-)\s*\d{1,2}:\d{2}\s*(am|pm)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\d{1,2}\s*(am|pm)\s*(?:to|-)\s*\d{1,2}\s*(am|pm)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\d{1,2}:\d{2}\s*(am|pm)\s*(?:to|-)\s*\d{1,2}\s*(am|pm)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\d{1,2}\s*(am|pm)\s*(?:to|-)\s*\d{1,2}:\d{2}\s*(am|pm)", "", cleaned, flags=re.I)

    cleaned = re.sub(
        r"\b(every other|every|biweekly)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        "",
        cleaned,
        flags=re.I,
    )

    for w in DATE_WORDS:
        cleaned = cleaned.replace(w, "")

    cleaned = re.sub(r"\bin\s+\d+\s+(hour|hours|minute|minutes|day|days)\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bon\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bat\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


def _clean_delete_title(user_input):
    cleaned = user_input.lower()
    cleaned = re.sub(r"^delete\s+", "", cleaned)
    cleaned = re.sub(r"^all\s+", "", cleaned)
    cleaned = re.sub(r"^one\s+", "", cleaned)
    cleaned = re.sub(r"\bon\b.*$", "", cleaned).strip()
    return cleaned


def parse_command(user_input, default_calendar="Calendar", default_duration_minutes=None):
    if default_duration_minutes is None:
        default_duration_minutes = DEFAULT_DURATION_MINUTES

    original_input = user_input
    user_input_lower = user_input.lower()

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

    result = {
        "intent": intent,
        "title": "",
        "start": None,
        "end": None,
        "calendar": default_calendar,
        "recurrence": None,
        "delete_mode": "single",
    }

    if intent == "delete":
        if user_input_lower.startswith("delete all"):
            result["delete_mode"] = "all"
        elif user_input_lower.startswith("delete one"):
            result["delete_mode"] = "single"
        else:
            result["delete_mode"] = "single"

        title_part = _clean_delete_title(original_input)
        result["title"] = _extract_title_spacy(title_part) if title_part else ""

        if " on " in user_input_lower:
            on_part = original_input.lower().split(" on ", 1)[1].strip()
            parsed_date = _parse_date_from_string(on_part)
            tr = _parse_time_range(on_part)

            if parsed_date and tr:
                sh, sm, sap, eh, em, eap = tr
                sh24, sm24 = _to_24h(sh, sm, sap)
                result["start"] = parsed_date.replace(hour=sh24, minute=sm24, second=0, microsecond=0)

        return result

    if intent == "list_week":
        return result

    if intent == "remind":
        title_part = user_input_lower.replace("remind me to", "", 1).strip()
        result["title"] = title_part.title() if title_part else "Reminder"

        date_keywords = (
            "tomorrow", "today", "next", "tonight", "noon", "morning",
            "afternoon", "evening", "at ", "on monday", "on tuesday",
            "on wednesday", "on thursday", "on friday", "on saturday", "on sunday"
        )
        if any(k in user_input_lower for k in date_keywords):
            when = _parse_date_from_string(original_input)
            if when:
                result["start"] = when
                result["end"] = when + timedelta(minutes=1)
        return result

    if intent == "modify":
        to_match = re.search(r"\bto\b", user_input_lower)
        if not to_match:
            raise ValueError("Modify format: modify <title> to <new time>")

        before_to = original_input[:to_match.start()].replace("modify", "", 1).strip()
        after_to = original_input[to_match.end():].strip()

        result["title"] = _extract_title_spacy(before_to) if before_to else ""

        parsed_date = _parse_date_from_string(after_to)
        if not parsed_date:
            raise ValueError("Could not detect new date/time for modify.")

        tr = _parse_time_range(after_to)
        if tr:
            sh, sm, sap, eh, em, eap = tr
            sh24, sm24 = _to_24h(sh, sm, sap)
            eh24, em24 = _to_24h(eh, em, eap)
            start_date = parsed_date.replace(hour=sh24, minute=sm24, second=0, microsecond=0)
            end_date = parsed_date.replace(hour=eh24, minute=em24, second=0, microsecond=0)
        else:
            start_date = parsed_date
            end_date = start_date + timedelta(minutes=default_duration_minutes)

        result["start"] = start_date
        result["end"] = end_date
        return result

    if intent == "add":
        tr = _parse_time_range(user_input_lower)
        recurrence = _parse_recurrence(user_input_lower)

        input_for_date = re.sub(r"for\s+\d+\s+weeks?", "", user_input_lower, flags=re.I)
        parsed_date = _parse_date_from_string(input_for_date)

        if not parsed_date:
            raise ValueError("Could not detect date.")

        if tr:
            sh, sm, sap, eh, em, eap = tr
            sh24, sm24 = _to_24h(sh, sm, sap)
            eh24, em24 = _to_24h(eh, em, eap)
            start_date = parsed_date.replace(hour=sh24, minute=sm24, second=0, microsecond=0)
            end_date = parsed_date.replace(hour=eh24, minute=em24, second=0, microsecond=0)
        else:
            start_date = parsed_date
            end_date = start_date + timedelta(minutes=default_duration_minutes)

        title_fragment = _title_cleaned_for_add(original_input)
        result["title"] = _extract_title_spacy(title_fragment) if title_fragment else "Event"
        result["start"] = start_date
        result["end"] = end_date
        result["recurrence"] = recurrence
        return result

    return result