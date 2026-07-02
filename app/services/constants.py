FALLBACK_RESPONSE = "I don't have that information yet. Please call Kabisa at 6420."

BLOCKED_PERSONA_TERMS = (
    "uri subiza",
    "ndi uri subiza",
    "created by ejo labs",
    "wakozwe na ejo labs",
    "ejo labs",
    "umufasha wa ai",
)


def looks_like_default_persona(answer):
    normalized = answer.lower()
    return any(term in normalized for term in BLOCKED_PERSONA_TERMS)
