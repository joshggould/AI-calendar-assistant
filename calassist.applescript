on run argv
    set command to item 1 of argv
    
    if command is "add" then
        my add_event(argv)
    else if command is "delete_all" then
        my delete_all_events(argv)
    else if command is "delete_one" then
        my delete_one_occurrence(argv)
    else if command is "modify" then
        my modify_event(argv)
    else if command is "list_week" then
        my list_week_events(argv)
    else if command is "check_conflict" then
        my check_conflict(argv)
    else if command is "add_reminder" then
        my add_reminder(argv)
    end if
end run


on add_event(argv)
    set cal_name to item 2 of argv
    set event_title to item 3 of argv
    set startTime to date (item 4 of argv)
    set endTime to date (item 5 of argv)
    
    tell application "Calendar"
        tell calendar cal_name
            set newEvent to make new event with properties {summary:event_title, start date:startTime, end date:endTime}
            
            if (count of argv) ³ 6 then
                set recurrenceRule to item 6 of argv
                if recurrenceRule is not "" then
                    try
                        set recurrence of newEvent to recurrenceRule
                    end try
                end if
            end if
        end tell
    end tell
    
    return "Event added successfully"
end add_event


on delete_all_events(argv)
    set cal_name to item 2 of argv
    set event_title to item 3 of argv
    
    tell application "Calendar"
        tell calendar cal_name
            set matchingEvents to every event whose summary is event_title
            repeat with e in matchingEvents
                delete e
            end repeat
        end tell
    end tell
    
    return "All matching events deleted"
end delete_all_events


on delete_one_occurrence(argv)
    set cal_name to item 2 of argv
    set event_title to item 3 of argv
    set targetStart to date (item 4 of argv)
    
    tell application "Calendar"
        tell calendar cal_name
            set matchingEvents to every event whose summary is event_title
            
            repeat with e in matchingEvents
                try
                    if ((start date of e) as date) = targetStart then
                        delete e
                        return "Single event occurrence deleted"
                    end if
                end try
                
                try
                    set existingExcluded to excluded dates of e
                    if existingExcluded is missing value then set existingExcluded to {}
                    
                    if recurrence of e is not missing value then
                        set excluded dates of e to existingExcluded & {targetStart}
                        return "Single recurring occurrence excluded"
                    end if
                end try
            end repeat
        end tell
    end tell
    
    return "No matching occurrence found"
end delete_one_occurrence


on modify_event(argv)
    set cal_name to item 2 of argv
    set event_title to item 3 of argv
    set newStart to date (item 4 of argv)
    set newEnd to date (item 5 of argv)
    
    tell application "Calendar"
        tell calendar cal_name
            set matchingEvents to every event whose summary is event_title
            repeat with e in matchingEvents
                set start date of e to newStart
                set end date of e to newEnd
            end repeat
        end tell
    end tell
    
    return "Event modified"
end modify_event


on list_week_events(argv)
    set cal_name to item 2 of argv
    
    set todayDate to current date
    set endOfWeek to todayDate + (7 * days)
    
    tell application "Calendar"
        tell calendar cal_name
            set weekEvents to every event whose start date ³ todayDate and start date ² endOfWeek
            
            set outputText to ""
            repeat with e in weekEvents
                set outputText to outputText & (summary of e) & " | " & (start date of e as string) & return
            end repeat
        end tell
    end tell
    
    return outputText
end list_week_events


on check_conflict(argv)
    set cal_name to item 2 of argv
    set propStart to date (item 3 of argv)
    set propEnd to date (item 4 of argv)
    
    tell application "Calendar"
        tell calendar cal_name
            set conflicts to every event whose (start date < propEnd and end date > propStart)
            if (count of conflicts) > 0 then
                return "CONFLICT"
            else
                return "NO_CONFLICT"
            end if
        end tell
    end tell
end check_conflict


on add_reminder(argv)
    set reminder_title to item 2 of argv
    set dueTime to missing value
    
    if (count of argv) ³ 3 and (item 3 of argv) is not "" then
        set dueTime to date (item 3 of argv)
    end if
    
    tell application "Reminders"
        set targetList to first list
        set newReminder to make new reminder at end of targetList
        set name of newReminder to reminder_title
        if dueTime is not missing value then
            set due date of newReminder to dueTime
        end if
    end tell
    
    return "Reminder added successfully"
end add_reminder