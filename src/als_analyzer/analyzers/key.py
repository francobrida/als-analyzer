"""Key: estimate the musical key of audio clips from their sample names.

Everything here is a guess from file names (plus the clip's transposition),
so every message says "estimated".
"""

from __future__ import annotations

import re
from collections import Counter
from typing import NamedTuple

from ..model import Clip, Finding, Session

NAME = "key"
ORDER = 40

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_PITCH = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Mode name -> semitones from the mode's root down to the tonic of its parent major scale.
# (A minor shares its notes with C major: C is 9 semitones above A, i.e. -9 = +3 mod 12.)
_PARENT_OFFSET = {
    "major": 0, "minor": 3, "dorian": 10, "phrygian": 8, "lydian": 7, "mixolydian": 5, "locrian": 1,
}
_MODE_ALIASES = {
    "min": "minor", "minor": "minor", "m": "minor", "aeolian": "minor",
    "maj": "major", "major": "major", "ionian": "major",
    "dorian": "dorian", "phrygian": "phrygian", "lydian": "lydian",
    "mixolydian": "mixolydian", "locrian": "locrian",
}

# Root, optional accidental, optional mode. The note must be a whole token: "D#2" (note + octave),
# "Bass" or "Dmitri" must not match. A bare letter ("_A.wav") is accepted, mode unknown.
_KEY = re.compile(
    r"(?<![A-Za-z0-9])([A-Ga-g])([#b♯♭]?)"
    r"(?:[ _-]?(?i:(minor|major|min|maj|phrygian|dorian|lydian|mixolydian|locrian|aeolian|ionian))|(m))?"
    r"(?![A-Za-z0-9#])"
)


class Key(NamedTuple):
    root: int  # pitch class, 0 = C
    mode: str | None  # None when the name only gives a note ("_A.wav")

    def __str__(self) -> str:
        return f"{NOTES[self.root]} {self.mode}" if self.mode else f"{NOTES[self.root]} (mode unknown)"

    def parents(self) -> set[int]:
        """Tonic(s) of the major scale holding the same notes; unknown mode could be major or minor."""
        offsets = [_PARENT_OFFSET[self.mode]] if self.mode else [0, 3]
        return {(self.root + o) % 12 for o in offsets}


def compatible(a: Key, b: Key) -> bool:
    """Same diatonic collection (so A minor ~ C major ~ D dorian)."""
    return bool(a.parents() & b.parents())


def parse_key(name: str) -> Key | None:
    for m in _KEY.finditer(name):
        letter, accidental, long_mode, short_m = m.groups()
        # A lowercase letter alone ("a", "am") is just a word; only "amin", "bbphrygian"... count.
        if letter.islower() and not long_mode:
            continue
        root = _PITCH[letter.upper()] + {"#": 1, "♯": 1, "b": -1, "♭": -1}.get(accidental, 0)
        raw_mode = long_mode or short_m
        return Key(root % 12, _MODE_ALIASES[raw_mode.lower()] if raw_mode else None)
    return None


def _sample_stem(path: str) -> str:
    filename = re.split(r"[\\/]", path)[-1]
    return filename.rsplit(".", 1)[0] if "." in filename else filename


def clip_key(clip: Clip) -> Key | None:
    """Key from the sample file name (falling back to the clip name), transposed by the clip."""
    key = (clip.sample_path and parse_key(_sample_stem(clip.sample_path))) or parse_key(clip.name)
    if key is None:
        return None
    # ponytail: Live ignores Transpose on unwarped clips; fine-tune cents are not considered.
    shift = clip.pitch_coarse if clip.is_warped else 0
    return Key((key.root + shift) % 12, key.mode)


def analyze(session: Session) -> list[Finding]:
    track_keys: dict[int, Counter[Key]] = {}
    for t in session.tracks:
        counts = Counter(k for c in t.clips if c.kind == "audio" and not c.disabled and (k := clip_key(c)))
        if counts:
            track_keys[t.id] = counts
    if not track_keys:
        return [Finding(NAME, "info", "No key information found in sample names")]

    by_id = {t.id: t for t in session.tracks}
    totals = sum(track_keys.values(), Counter())
    # Reference: the key supported by most clips (counting compatible ones), preferring known modes.
    ref = max(
        totals,
        key=lambda k: (sum(n for o, n in totals.items() if compatible(k, o)), k.mode is not None, totals[k]),
    )
    support = sum(n for o, n in totals.items() if compatible(ref, o))
    findings = [
        Finding(NAME, "info", f"Session key (estimated): {ref}, {support} of {sum(totals.values())} keyed clips")
    ]

    for tid, counts in track_keys.items():
        t = by_id[tid]
        if len(counts) > 1:
            keys = ", ".join(str(k) for k in counts)
            findings.append(Finding(NAME, "warning", f"Several keys in one track (estimated): {keys}", t.name, t.id))
        elif not compatible(next(iter(counts)), ref):
            only = next(iter(counts))
            # A bare note ("... 128 BPM G") is weak evidence, so it is not worth a warning.
            findings.append(
                Finding(
                    NAME, "warning" if only.mode else "info",
                    f"Key {only} (estimated) does not match session key {ref}",
                    t.name, t.id,
                )
            )
    return findings
