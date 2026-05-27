"""
Critic name deduplication.

Critics change publications over time. "Ben Brantley" at NYT and
"Ben Brantley" at another outlet are the same person. We use
(normalized_name) as the primary identity, with publication as secondary.

If the same normalized name appears at two publications, we keep separate
records but flag them as potential duplicates for manual review.
"""
import re
from typing import Optional


def normalize_critic_name(name: str) -> str:
    """Lowercase, strip honorifics and punctuation."""
    n = name.strip()
    # Remove common honorifics
    n = re.sub(r"^(Mr\.|Ms\.|Mrs\.|Dr\.|Prof\.)\s+", "", n, flags=re.I)
    n = re.sub(r"[^a-zA-Z\s'-]", "", n)
    n = re.sub(r"\s+", " ", n).lower().strip()
    return n


def is_house_critic(critic_name: str, publication: str) -> bool:
    """Return True if this critic is known as a regular staffer at that publication."""
    known_house_critics = {
        "new york times": {"ben brantley", "jesse green", "charles isherwood",
                           "helen shaw", "elisabetta povoledo"},
        "variety": {"frank rizzo", "marilyn stasio", "gordon cox"},
        "time out new york": {"adam feldman"},
        "vulture": {"sara holdren", "helen shaw"},
        "new york post": {"johnny oleksinski"},
        "new york daily news": {"joe dziemianowicz", "chris jones"},
    }
    pub_norm = publication.lower().strip()
    critic_norm = normalize_critic_name(critic_name)
    for pub_key, critics in known_house_critics.items():
        if pub_key in pub_norm:
            return critic_norm in critics
    return False
