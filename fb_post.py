"""Post products to Facebook Marketplace using OS-level automation.
Connects to already-open Chrome session via pyautogui (mouse+keyboard control).
"""
import pyautogui
import time
import sys

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

PRODUCTS = [
    {
        "name": "LED Strip Lights RGB 16 Colors",
        "description": "Color-changing LED strip lights with remote control. 16 vibrant colors, multiple lighting modes. USB powered. Perfect for bedroom, gaming setup, dorm room, or party decor. Brand new, ships fast!",
        "price": "6",
        "image": r"C:\Users\lokas\projects\zero-human-dropship-revenue\product_images\led_strip.jpg",
    },
    {
        "name": "Magnetic Phone Mount for Car",
        "description": "Ultra-strong magnetic car phone holder. Sticks to any dashboard or vent. Works with all phones. 360-degree rotation. Easy install, no tools needed.",
        "price": "5",
        "image": r"C:\Users\lokas\projects\zero-human-dropship-revenue\product_images\phone_mount.jpg",
    },
    {
        "name": "Portable Mini Fan USB",
        "description": "Compact USB desk fan with 3 speeds. Whisper quiet operation. Perfect for office, dorm, or travel. USB-C powered, works with any power bank.",
        "price": "5",
        "image": r"C:\Users\lokas\projects\zero-human-dropship-revenue\product_images\mini_fan.jpg",
    },
    {
        "name": "Wireless Earbuds with Charging Case",
        "description": "True wireless Bluetooth earbuds with noise isolation. 20-hour battery with charging case. Touch controls. Works with iPhone and Android.",
        "price": "8",
        "image": r"C:\Users\lokas\projects\zero-human-dropship-revenue\product_images\earbuds.jpg",
    },
    {
        "name": "Phone Ring Light for Selfies",
        "description": "Clip-on ring light for your phone. 3 brightness levels. Rechargeable battery. Perfect for selfies, video calls, and TikTok content creation.",
        "price": "4",
        "image": r"C:\Users\lokas\projects\zero-human-dropship-revenue\product_images\ring_light.jpg",
    },
    {
        "name": "Cable Organizer Clips 10-Pack",
        "description": "Keep your desk clean with self-adhesive cable management clips. Pack of 10. Sticks to wood, glass, and plastic. No more tangled cords!",
        "price": "3",
        "image": r"C:\Users\lokas\projects\zero-human-dropship-revenue\product_images\cable_clips.jpg",
    },
    {
        "name": "Foldable Phone Stand Adjustable",
        "description": "Aluminum alloy foldable phone and tablet stand. Adjustable angle. Anti-slip pads. Folds flat for travel. Works with all phones and tablets.",
        "price": "6",
        "image": r"C:\Users\lokas\projects\zero-human-dropship-revenue\product_images\phone_stand.jpg",
    },
    {
        "name": "Screen Cleaner Spray Kit",
        "description": "Streak-free screen cleaner for phones, laptops, and tablets. Includes microfiber cloth. Travel-sized bottle. Safe for all screens.",
        "price": "4",
        "image": r"C:\Users\lokas\projects\zero-human-dropship-revenue\product_images\screen_cleaner.jpg",
    },
    {
        "name": "USB-C Fast Charging Cable 6ft",
        "description": "Braided nylon USB-C cable. Fast charging up to 60W. 6-foot length for convenience. Durable connectors. Works with Samsung, Pixel, iPad.",
        "price": "5",
        "image": r"C:\Users\lokas\projects\zero-human-dropship-revenue\product_images\usbc_cable.jpg",
    },
    {
        "name": "Laptop Cooling Pad with Fan",
        "description": "Slim laptop cooling pad with quiet fan. Fits up to 15.6 inch laptops. USB powered. Adjustable height. Prevents overheating during gaming or work.",
        "price": "9",
        "image": r"C:\Users\lokas\projects\zero-human-dropship-revenue\product_images\cooling_pad.jpg",
    },
]


def type_slow(text, interval=0.02):
    """Type text character by character to avoid Facebook dropping input."""
    for char in text:
        pyautogui.write(char, interval=0) if char.isascii() and char.isprintable() else pyautogui.press('space')
        time.sleep(interval)


def fill_description_only():
    """Just fill the description field on the currently open listing page.
    The listing should already have photo, title, price, category, condition set.
    """
    print("You have 3 seconds to make sure the Facebook listing page is visible...")
    time.sleep(3)

    # Click on the description field area (center-left of screen, roughly where it is)
    # Based on screenshot: description field is at approximately x=219, y=345 on a 1568x773 viewport
    # But pyautogui uses screen coordinates, not viewport. Let's click where we see it.
    print("Clicking description field...")
    pyautogui.click(219, 580)  # approximate screen coords (account for chrome toolbar)
    time.sleep(0.5)

    print("Typing description...")
    # Use clipboard paste for reliability
    import pyperclip
    desc = PRODUCTS[0]["description"]
    pyperclip.copy(desc)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1)

    print("Done! Check the description field.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--desc-only":
        fill_description_only()
        return

    print("=== Facebook Marketplace Auto-Poster ===")
    print("This will type the description into the currently open listing.")
    print("Make sure the FB Marketplace 'Create Listing' page is visible.")
    print()
    print("Starting in 3 seconds... (move mouse to top-left corner to abort)")
    time.sleep(3)

    # Just paste the description via clipboard - most reliable method
    import pyperclip

    desc = PRODUCTS[0]["description"]
    print(f"Pasting description: {desc[:50]}...")

    # Click the description field
    pyautogui.click(219, 580)
    time.sleep(0.5)

    # Paste via clipboard
    pyperclip.copy(desc)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1)

    print("Description pasted! Check the browser.")
    print("If it worked, press Enter to continue to clicking Next...")
    input()

    # Scroll down and click Next
    pyautogui.click(219, 730)  # Next button area
    time.sleep(2)

    print("Done with first listing!")


if __name__ == "__main__":
    main()
