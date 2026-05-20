"""
Caz — CLI Entry Point

The main interface where you talk to Caz.
This is the terminal chat loop with Caz's personality.

Teaching note: This module handles I/O (input/output) only.
It doesn't contain logic — that lives in the Engine.
Separation of concerns: I/O here, logic there.
"""

import sys
from pathlib import Path

from core.engine import Engine


# --- Caz's Personality ---
# These strings give Caz its whimsical, bookish character.
# Named after a magical plant in an enchanted greenhouse,
# Caz speaks with a touch of wonder and warmth.

BANNER = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   🌱  C A Z                                             ║
║                                                          ║
║   A seedling of knowledge, growing in your greenhouse.   ║
║   Truly open. Locally rooted. Endlessly curious.         ║
║                                                          ║
║   Type 'help' for commands, or just start talking.       ║
║   Type 'quit' when you need to step away.                ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""

GREETING_MESSAGES = [
    "✨ *stretches leaves toward the light* — Good to see you. What shall we explore today?",
    "🌿 The greenhouse is warm and quiet. I'm ready when you are.",
    "📚 *rustles pages* — I've been reading while you were away. What's on your mind?",
    "🌱 Another day, another chance to grow. What are we learning?",
    "✨ The ink is fresh, the pages are open. Let's begin.",
]

FAREWELL_MESSAGES = [
    "🌙 Rest well. I'll be here, tending to what we've planted.",
    "📖 *closes the book gently* — Until next time, fellow traveler.",
    "🌿 The greenhouse keeps growing, even while you're away. See you soon.",
    "✨ May your path be lit with curiosity. Goodbye for now.",
    "🌱 Every ending is a seed for tomorrow. Take care.",
]

THINKING_PREFIX = "🌿 "

# The prompt character — like a little sprout waiting for input
PROMPT = "\n🌱 you › "


def get_greeting() -> str:
    """Pick a greeting based on simple rotation."""
    from datetime import datetime

    # Use the current hour to rotate greetings throughout the day
    hour = datetime.now().hour
    index = hour % len(GREETING_MESSAGES)
    return GREETING_MESSAGES[index]


def get_farewell() -> str:
    """Pick a farewell message."""
    from datetime import datetime

    minute = datetime.now().minute
    index = minute % len(FAREWELL_MESSAGES)
    return FAREWELL_MESSAGES[index]


def format_response(text: str) -> str:
    """
    Format Caz's response for display.

    Adds the thinking prefix and wraps for terminal readability.
    """
    lines = text.strip().split("\n")
    formatted = []
    for i, line in enumerate(lines):
        if i == 0:
            formatted.append(f"{THINKING_PREFIX}{line}")
        else:
            formatted.append(f"  {line}")
    return "\n".join(formatted)


def run():
    """
    Main chat loop.

    Teaching note: This is an "event loop" — it waits for input,
    processes it, shows output, and repeats. Most interactive
    programs follow this pattern. Web servers, games, and chat
    apps all work this way at their core.
    """
    # Initialize the engine
    try:
        engine = Engine()
    except ValueError as e:
        print(f"❌ Configuration error:\n{e}")
        print("   Fix config.toml and try again.")
        sys.exit(1)

    # Show banner and greeting
    print(BANNER)
    print(format_response(get_greeting()))

    # The loop — Caz listens, thinks, responds
    while True:
        try:
            user_input = input(PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            # Ctrl+C or Ctrl+D — graceful exit
            print()
            print(format_response(get_farewell()))
            break

        # Skip empty input
        if not user_input:
            continue

        # Send to engine for processing
        response = engine.process_message(user_input)

        # Check for exit signal
        if response == "__EXIT__":
            print(format_response(get_farewell()))
            break

        # Display Caz's response
        print(format_response(response))


if __name__ == "__main__":
    run()
