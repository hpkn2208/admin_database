"""Visits the deployed Streamlit app like a real browser so its inactivity
timer resets, and clicks the "wake up" button if Streamlit Cloud already put
it to sleep. A bare curl/HTTP GET doesn't reliably do either — Streamlit only
counts a real script run (over the app's WebSocket connection) as activity.

Same approach as streamlit_app/.github/scripts/keep_awake.py, adapted for
this app's login-gated page (waits for the "Password" field instead of any
post-login content — this script never logs in, it just wakes the app).
"""

import os
import sys

from playwright.sync_api import sync_playwright

APP_URL = os.environ["APP_URL"]


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        # networkidle never fires for Streamlit (persistent WebSocket keeps
        # traffic going), so just wait for the HTML shell and poll for content.
        page.goto(APP_URL, wait_until="domcontentloaded", timeout=60_000)

        wake_button = page.get_by_text("get this app back up", exact=False)
        try:
            wake_button.first.wait_for(state="visible", timeout=20_000)
            print("App was asleep — clicking wake-up button.")
            wake_button.first.click()
            # Cold boot (container spin-up) can take a while.
            page.wait_for_selector("text=Password", timeout=180_000)
            print("App finished waking up.")
        except Exception:
            print("No wake-up button seen — app was likely already awake.")

        browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Failed to ping {APP_URL}: {exc}", file=sys.stderr)
        raise
