"""Tests to validate Firestore security rules invariants and access control."""

import re
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent.parent.parent / "firestore.rules"


def test_firestore_rules_file_exists():
    """Verify that firestore.rules exists at project root."""
    assert RULES_PATH.exists(), f"firestore.rules not found at {RULES_PATH}"


def test_firestore_rules_invariants():
    """Verify all security constitution invariants for Firestore rules."""
    content = RULES_PATH.read_text()

    # Invariant 1: No permissive rules anywhere in the file
    assert "if true" not in content, "VIOLATION: 'if true' found in firestore.rules"

    # Invariant 2: Single owner-bound wildcard rule
    assert "match /users/{userId}/{document=**}" in content, (
        "VIOLATION: Single owner-bound wildcard rule 'match /users/{userId}/{document=**}' missing."
    )

    # Invariant 3: Rule checks request.auth != null and request.auth.uid == userId
    assert "request.auth != null" in content
    assert "request.auth.uid == userId" in content

    # Invariant 4: Deny-all fallback for everything else
    assert "match /{document=**}" in content
    assert "allow read, write: if false;" in content

    # Invariant 5: No per-subcollection rules (e.g. match /journals/ or match /config/)
    # A narrower match would violate Invariant 3 by creating sibling leakage risk
    forbidden_subcollection_matches = [
        r"match\s+/users/\{userId\}/journals",
        r"match\s+/users/\{userId\}/config",
        r"match\s+/users/\{userId\}/sessions",
        r"match\s+/users/\{userId\}/stats",
        r"match\s+/users/\{userId\}/subscription",
        r"match\s+/interactions",
        r"match\s+/journals",
    ]
    for pattern in forbidden_subcollection_matches:
        assert not re.search(pattern, content), (
            f"VIOLATION: Found narrower subcollection match for {pattern}. "
            "Architecture Invariant 3 requires a single owner-bound wildcard rule."
        )
