on run argv
    
    set command to item 1 of argv
    
    if command is "add" then
        my add_event(argv)
        
    else if command is "delete" then
        my delete_event(argv)
        
    else if command is "modify" then
        my modify_event(argv)
        
    else if command is "list_week" then
        my list_week_events()
        
    else if command is "check_conflict" then
        my check_conflict(argv)
        
    end if
    
end run


-- ===============================
-- ADD EVENT
-- ===============================
on add_event(argv)
    
    set event_title to item 2 of argv
    set start_date to date (item 3 of argv)
    set end_date to date (item 4 of argv)
    
    tell application "Calendar"
        tell calendar "Calendar"
            make new event with properties {summary:event_title, start date:start_date, end date:end_date}
        end tell
    end tell
    
    return "Event added successfully"
    
end add_event



-- ===============================
-- DELETE EVENT
-- ===============================
on delete_event(argv)
    
    set event_title to item 2 of argv
    
    tell application "Calendar"
        tell calendar "Calendar"
            set matchingEvents to every event whose summary is event_title
            
            repeat with e in matchingEvents
                delete e
            end repeat
        end tell
    end tell
    
    return "Event deleted"
    
end delete_event



-- ===============================
-- MODIFY EVENT
-- ===============================
on modify_event(argv)
    
    set event_title to item 2 of argv
    set new_start to date (item 3 of argv)
    set new_end to date (item 4 of argv)
    
    tell application "Calendar"
        tell calendar "Calendar"
            set matchingEvents to every event whose summary is event_title
            
            repeat with e in matchingEvents
                set start date of e to new_start
                set end date of e to new_end
            end repeat
        end tell
    end tell
    
    return "Event modified"
    
end modify_event



-- ===============================
-- LIST THIS WEEK'S EVENTS
-- ===============================
on list_week_events()
    
    set todayDate to current date
    set endOfWeek to todayDate + (7 * days)
    
    tell application "Calendar"
        tell calendar "Calendar"
            set weekEvents to every event whose start date ³ todayDate and start date ² endOfWeek
            
            set outputText to ""
            
            repeat with e in weekEvents
                set outputText to outputText & (summary of e) & " | " & (start date of e as string) & return
            end repeat
            
        end tell
    end tell
    
    return outputText
    
end list_week_events



-- ===============================
-- CHECK CONFLICT
-- ===============================
on check_conflict(argv)
    
    set proposed_start to date (item 2 of argv)
    set proposed_end to date (item 3 of argv)
    
    tell application "Calendar"
        tell calendar "Calendar"
            set conflicts to every event whose (start date < proposed_end and end date > proposed_start)
            
            if (count of conflicts) > 0 then
                return "CONFLICT"
            else
                return "NO_CONFLICT"
            end if
            
        end tell
    end tell
    
end check_conflict
