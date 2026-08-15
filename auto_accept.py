"""Auto-accept Claude Code permission prompts by sending Enter keystrokes."""
import time
import pyautogui

print("=== Auto-Accept Started ===")
print("Pressing Enter every 0.5 seconds to auto-accept Claude Code prompts.")
print("Press Ctrl+C to stop.")
print()

while True:
    pyautogui.press('enter')
    time.sleep(0.5)
