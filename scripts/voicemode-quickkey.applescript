-- voicemode-quickkey.applescript
-- Global hotkey action: activate VoiceMode in the "Chief of Staff" terminal window.
-- Designed to be run from a macOS Shortcut assigned to Ctrl+Shift+V.

-- Record the currently frontmost application
set previousApp to (path to frontmost application as text)

-- Search Terminal.app for a window titled "Chief of Staff"
set windowFound to false

tell application "Terminal"
	repeat with w in windows
		if name of w contains "Chief of Staff" then
			set windowFound to true
			-- Bring Terminal to front and target this window
			activate
			set index of w to 1

			-- Type the VoiceMode command and press Enter
			delay 0.2
			tell application "System Events"
				tell process "Terminal"
					keystroke "/voicemode:converse"
					delay 0.1
					keystroke return
				end tell
			end tell

			-- Brief pause, then return focus to the previous app
			delay 0.5
			tell application previousApp to activate

			exit repeat
		end if
	end repeat
end tell

-- If no matching window was found, show a notification
if not windowFound then
	display notification "No 'Chief of Staff' terminal window found. Launch it with scripts/cos-launch.sh" with title "VoiceMode Quick Key"
end if
