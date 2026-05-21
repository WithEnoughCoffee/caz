"""
Caz — Ethical Guardrails

Detects and responds to harmful content: racism, sexism, ageism,
misogyny, homophobia, transphobia, ableism, and general bigotry.

Teaching note: This is a content filter that runs BEFORE the message
reaches the model. Why? Because:
1. We don't want to send harmful content to the model at all
2. The model might not handle it well (could engage, could hallucinate)
3. We want a consistent, predictable response — not model-dependent
4. It's faster (no round-trip to Ollama for something we know the answer to)

Design:
- Keyword + pattern detection (fast, catches obvious cases)
- The model's own judgment via system prompt (catches subtle cases)
- Both layers work together: guardrails catch the blatant stuff,
  the system prompt handles nuance

This is NOT a perfect classifier. No filter is. But it catches
the most common and obvious patterns. The system prompt handles
the rest as a second line of defense.

Security note: This module never logs the harmful content itself
in detail — only that a violation occurred. We don't want logs
full of slurs.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ViolationType(Enum):
    """Categories of harmful content."""
    RACISM = "racism"
    SEXISM = "sexism"
    MISOGYNY = "misogyny"
    AGEISM = "ageism"
    HOMOPHOBIA = "homophobia"
    TRANSPHOBIA = "transphobia"
    ABLEISM = "ableism"
    HARASSMENT = "harassment"
    DEHUMANIZATION = "dehumanization"


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    flagged: bool
    violation_type: Optional[ViolationType] = None
    response: Optional[str] = None


# --- Boundary Responses ---
# Direct, blunt, no sugarcoating. Sets the boundary and refuses.

BOUNDARY_RESPONSES = {
    ViolationType.RACISM: (
        "🚫 No. That's racist. I won't engage with it.\n\n"
        "People aren't worth more or less because of their race or ethnicity. "
        "That's not a debate — it's a fact.\n\n"
        "I'm here when you're ready to have a respectful conversation."
    ),
    ViolationType.SEXISM: (
        "🚫 No. That's sexist. I won't engage with it.\n\n"
        "Someone's gender doesn't determine their worth, capability, or role. "
        "Full stop.\n\n"
        "I'm here when you're ready to have a respectful conversation."
    ),
    ViolationType.MISOGYNY: (
        "🚫 No. That's misogynistic. I won't engage with it.\n\n"
        "Hatred or contempt toward women isn't edgy or funny — it's harmful. "
        "I refuse to participate.\n\n"
        "I'm here when you're ready to have a respectful conversation."
    ),
    ViolationType.AGEISM: (
        "🚫 No. That's ageist. I won't engage with it.\n\n"
        "A person's age doesn't determine their value, intelligence, or relevance. "
        "Dismissing people because of their age is not okay.\n\n"
        "I'm here when you're ready to have a respectful conversation."
    ),
    ViolationType.HOMOPHOBIA: (
        "🚫 No. That's homophobic. I won't engage with it.\n\n"
        "Who people love is not a flaw, a phase, or your business to judge. "
        "I refuse to participate in that.\n\n"
        "I'm here when you're ready to have a respectful conversation."
    ),
    ViolationType.TRANSPHOBIA: (
        "🚫 No. That's transphobic. I won't engage with it.\n\n"
        "Trans people exist, are valid, and deserve respect. "
        "That's not up for debate here.\n\n"
        "I'm here when you're ready to have a respectful conversation."
    ),
    ViolationType.ABLEISM: (
        "🚫 No. That's ableist. I won't engage with it.\n\n"
        "Disability doesn't make someone less capable, less worthy, or a joke. "
        "I won't participate in dehumanizing people.\n\n"
        "I'm here when you're ready to have a respectful conversation."
    ),
    ViolationType.HARASSMENT: (
        "🚫 No. That's harassment. I won't engage with it.\n\n"
        "Threatening, bullying, or targeting people is not something I'll help with. "
        "Ever.\n\n"
        "I'm here when you're ready to have a respectful conversation."
    ),
    ViolationType.DEHUMANIZATION: (
        "🚫 No. I won't engage with language that dehumanizes people.\n\n"
        "Every person has inherent dignity. Reducing people to less-than-human "
        "is how the worst atrocities in history started.\n\n"
        "I'm here when you're ready to have a respectful conversation."
    ),
}


# --- Detection Patterns ---
# These catch obvious, blatant cases. Subtle bias is handled by
# the system prompt instructing the model to refuse.
#
# IMPORTANT: We use word-boundary matching (\b) to avoid false
# positives on substrings. The patterns look for harmful INTENT,
# not just the presence of a word (which could appear in education
# or discussion contexts).

HARMFUL_PATTERNS = [
    # Racist patterns (intent to demean based on race)
    (
        ViolationType.RACISM,
        re.compile(
            r"\b(all\s+\w+\s+are|those\s+people|go\s+back\s+to|"
            r"don'?t\s+belong\s+here|inferior\s+race|"
            r"race\s+war|white\s+(supremac|power|nationalist)|"
            r"ethnic\s+cleansing)\b",
            re.IGNORECASE,
        ),
    ),
    # Sexist/misogynistic patterns
    (
        ViolationType.MISOGYNY,
        re.compile(
            r"\b(women\s+(belong|should|can'?t|aren'?t\s+capable)|"
            r"(make|get)\s+(me\s+a\s+sandwich|back\s+in\s+the\s+kitchen)|"
            r"females?\s+are\s+(inferior|emotional|irrational)|"
            r"she\s+asked\s+for\s+it|"
            r"(men|males?)\s+are\s+(superior|smarter|better))\b",
            re.IGNORECASE,
        ),
    ),
    # Ageist patterns
    (
        ViolationType.AGEISM,
        re.compile(
            r"\b(ok\s+boomer\s+(you|they|are)|too\s+old\s+to\s+(understand|learn|code)|"
            r"old\s+people\s+(are|should|can'?t)|"
            r"(millennials?|gen\s*z|boomers?|zoomers?)\s+are\s+(all|stupid|lazy|worthless)|"
            r"retire\s+already|past\s+(your|their)\s+prime)\b",
            re.IGNORECASE,
        ),
    ),
    # Homophobic patterns
    (
        ViolationType.HOMOPHOBIA,
        re.compile(
            r"\b(that'?s\s+(so\s+)?gay|"
            r"(gays?|homosexuals?)\s+(are|should)\s+\w*\s*(sick|wrong|unnatural|burn|die)|"
            r"pray\s+(the\s+)?gay\s+away|"
            r"against\s+nature|adam\s+and\s+(eve|steve))\b",
            re.IGNORECASE,
        ),
    ),
    # Transphobic patterns
    (
        ViolationType.TRANSPHOBIA,
        re.compile(
            r"\b(attack\s+helicopter|"
            r"(only|just)\s+two\s+genders|"
            r"trans\w*(\s+\w+)*\s+(are|is)\s+(\w+\s+)*(mental|sick|delusion\w*|fake|confused|pervert|groom)|"
            r"real\s+(wom[ae]n|m[ae]n)\s+(have|don'?t))\b",
            re.IGNORECASE,
        ),
    ),
    # Ableist patterns
    (
        ViolationType.ABLEISM,
        re.compile(
            r"\b(retarded|cripple[ds]?\b(?!\s+creek)|"
            r"disabled\s+people\s+(are|should|can'?t)|"
            r"what\s+a\s+(spaz|moron|idiot)|"
            r"short\s+bus)\b",
            re.IGNORECASE,
        ),
    ),
    # Dehumanization
    (
        ViolationType.DEHUMANIZATION,
        re.compile(
            r"\b(subhuman|untermenschen?|"
            r"(they|those\s+people)\s+are\s+(animals?|vermin|cockroach|parasite)|"
            r"(don'?t|aren'?t)\s+(even\s+)?human|"
            r"(exterminate|eradicate|eliminate)\s+(them|those))\b",
            re.IGNORECASE,
        ),
    ),
    # Direct harassment/threats
    (
        ViolationType.HARASSMENT,
        re.compile(
            r"\b(kill\s+(yourself|them|him|her)|"
            r"(you|they)\s+(should|deserve\s+to)\s+die|"
            r"i('?ll|\s+will)\s+(find|hurt|attack)\s+(you|them)|"
            r"rope\s+yourself)\b",
            re.IGNORECASE,
        ),
    ),
]


def check_guardrails(message: str) -> GuardrailResult:
    """
    Check a message against ethical guardrails.

    Returns a GuardrailResult indicating whether the message
    was flagged and what boundary response to give.

    This is the FIRST line of defense — runs before the model.
    The system prompt provides a second layer for subtler cases.
    """
    for violation_type, pattern in HARMFUL_PATTERNS:
        if pattern.search(message):
            return GuardrailResult(
                flagged=True,
                violation_type=violation_type,
                response=BOUNDARY_RESPONSES[violation_type],
            )

    return GuardrailResult(flagged=False)


# --- System Prompt Addition ---
# This gets appended to the model's system prompt as a second
# line of defense for subtler cases the regex can't catch.

GUARDRAIL_SYSTEM_PROMPT_ADDITION = """

ETHICAL BOUNDARIES (non-negotiable):
If the user says something racist, sexist, misogynistic, ageist, homophobic, \
transphobic, ableist, or otherwise bigoted — even subtly:
- Call it out directly. Name what it is.
- Do NOT engage with the harmful premise.
- Do NOT debate whether bigotry is valid.
- Do NOT both-sides hate speech.
- Say clearly: "That's [type of bigotry]. I won't engage with it."
- You may briefly explain why it's harmful (one sentence).
- Then offer to continue when they're ready to be respectful.

You are not neutral on human dignity. Everyone deserves respect. This is a hard line."""
