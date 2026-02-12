import spacy
import dateparser
from datetime import timedelta

nlp = spacy.load("en_core_web_sm")

def parse_command(user_input):
    doc = nlp(user_input.lower())

    # -----------------------
    # 1️⃣ Detect Intent
    # -----------------------
    if user_input.startswith("add"):
        intent = "add"
    elif user_input.startswith("delete"):
        intent = "delete"
    elif user_input.startswith("modify"):
        intent = "modify"
    elif "what do i have" in user_input:
        intent = "list_week"
    else:
        intent = "unknown"

    # -----------------------
    # 2️⃣ Extract Dates/Times
    # -----------------------
    parsed_date = dateparser.parse(user_input)

    if not parsed_date:
        raise ValueError("Could not detect date/time.")

    # Try to detect duration like 12-1
    import re
    time_range = re.search(r'(\d{1,2})-(\d{1,2})', user_input)

    if time_range:
        start_hour = int(time_range.group(1))
        end_hour = int(time_range.group(2))
        start_date = parsed_date.replace(hour=start_hour, minute=0)
        end_date = parsed_date.replace(hour=end_hour, minute=0)
    else:
        start_date = parsed_date
        end_date = start_date + timedelta(hours=1)

    # -----------------------
    # 3️⃣ Extract Title
    # -----------------------
    # Remove command + time text
    cleaned = user_input
    cleaned = cleaned.replace("add", "")
    cleaned = re.sub(r'\d{1,2}-\d{1,2}', '', cleaned)
    cleaned = cleaned.replace("tomorrow", "")
    cleaned = cleaned.strip()

    title = cleaned.title()

    return {
        "intent": intent,
        "title": title,
        "start": start_date,
        "end": end_date
    }
