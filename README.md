# als-analyzer

Read-only analyzer for Ableton Live (`.als`) sessions. **Know what a session needs before you open it.**

## What it is for

Opening a large session just to find out it is missing a plugin or a sample is slow and annoying. `als-analyzer` answers the practical questions up front, without launching Live:

- **Which third-party plugins does it need?** VST2/VST3/AU, per track and as a unique list, so you know what to install or whether you can collaborate on it.
- **What files does it depend on?** Samples that live outside the project folder, i.e. what would go missing when the session is moved, shared or archived.
- **Quick facts about the session:** Live version, BPM, track counts by type, return tracks.

These are the parts that are reliable and in daily use: `inventory`, `plugins` and `dependencies`. They read what is stored in the file as is, with no interpretation.

The other analyzers (`sections`, `density`, `key`, `routing`, `cleanup`) are **work in progress**. They rely on heuristics (guessing keys from file names, assuming 4/4, inferring structure from a guide track), so their output is a hint, not a fact. Treat it accordingly.

- **Read-only.** It never writes to the `.als`.
- **Safe input.** An `.als` is treated as untrusted: XML is parsed with [defusedxml](https://pypi.org/project/defusedxml/).
- **Tolerant.** Missing tags (other Live versions) become warnings instead of crashes.
- Checked against a real Live 12.4.3 session; accepts gzip-compressed `.als` and plain XML.

## Install

```bash
pip install -e ".[dev]"
```

Requires Python 3.10+.

## Usage

```bash
als-analyzer path/to/session.als
als-analyzer path/to/session.als --json
als-analyzer path/to/session.als --sections-track "ARRANGE"
als-analyzer path/to/session.als --open            # HTML report in your browser
als-analyzer path/to/session.als --html report.html
```

| Option | Meaning |
| --- | --- |
| `--json` | Print JSON instead of the terminal report. |
| `--html FILE` | Write a self-contained HTML report (one file, no JavaScript, works offline; light/dark theme). |
| `--open` | Open the HTML report in the browser. Uses a temp file unless `--html` is also given. |
| `--sections-track NAME` | MIDI track whose clips define the sections when the session has no locators (default `ARRANGE`). |

### Right-click on Windows

```bash
python -m als_analyzer.context_menu install     # adds "Analyze with als-analyzer" to .als files
python -m als_analyzer.context_menu uninstall
```

Per-user (no admin). The report opens in your browser with no console window. On Windows 11 it is under "Show more options".

Exit code is `1` if the file cannot be read or is not a Live set.

### Example output

Output for the synthetic session used in the tests (no real project data):

```
demo.als

inventory
  • Created with Ableton Live 12.4.3
  • Tempo: 133 BPM
  • Tracks: 2 audio, 1 MIDI, 1 groups
  • Return tracks: 1
  • Sections: 2 (INTRO, DROP)

sections
  • Sections from track 'ARRANGE' (bars assume 4/4)
  • INTRO: bar 1, 8 bars
  • DROP: bar 9, 16 bars

density
  • INTRO: 1 of 2 tracks playing
  • DROP: 0 of 2 tracks playing
  • Active clips per track and section

  Track   INTRO   DROP
 ──────────────────────
  Kick      1      ·
  Hat       ·      ·

key
  • Session key (estimated): B minor, 1 of 1 keyed clips

routing
  • [Drums] Bus receiving 1 track(s): Hat

cleanup
  • [Kick] 1 disabled clip(s): kick2
  ! [Hat] Empty track with 1 device(s) loaded
  • 1 track(s) never renamed: Hat

dependencies
  ! [Kick] 1 sample(s) outside the project folder: C:/Samples/kick_Amin.wav

plugins
  • 2 third-party plugin(s) needed: Serum (VST3), Sylenth1 (VST2)
  • [Kick] Serum (VST3)
  • [Hat] Sylenth1 (VST2)
```

`•` is informational, `!` is a warning. (Here the key is B minor because the kick sample is `..._Amin` transposed +2 semitones.)

## Analyzers

**Stable**

| Analyzer | What it reports |
| --- | --- |
| `plugins` | Third-party plugins (VST2/VST3/AU), per track and in total. |
| `dependencies` | Samples outside the project folder (the `... Project` folder containing the `.als`). |
| `inventory` | Live version, BPM, track counts by type, returns, sections. |

**Work in progress** (heuristic, may be inaccurate)

| Analyzer | What it reports |
| --- | --- |
| `sections` | Sections from locators or, if there are none, from the clips of a guide MIDI track. Bars assume 4/4. |
| `density` | Per section, how many tracks have active clips sounding, as a section × track table. |
| `key` | Key estimated from sample file names (`G#min`, `Amin`, `_A.wav`, `BPhrygian`; ignores `D#2`-style note + octave) plus the clip's transposition. Warns about tracks with several keys and tracks that clash with the session key. **Always an estimate.** |
| `routing` | Buses (tracks that receive other tracks) and tracks going straight to Main when most go through a bus. |
| `cleanup` | Disabled clips, empty tracks with devices loaded, tracks never renamed. |

## Architecture

```
src/als_analyzer/
├── model.py        # frozen dataclasses: Session, Track, Clip, Device, Section, Finding
├── parser.py       # .als -> model; the only module that knows the XML
├── analyzers/      # one module per check: NAME + analyze(session) -> list[Finding]
├── report.py       # terminal (rich) and JSON output
└── cli.py
```

Analyzers are discovered automatically. To add one, create `analyzers/my_check.py`:

```python
from ..model import Finding, Session

NAME = "my_check"
ORDER = 50  # optional, lower runs (and prints) first


def analyze(session: Session) -> list[Finding]:
    return [Finding(NAME, "info", "hello")]
```

A `Finding` has a severity (`info` / `warning`), a message, an optional track and an optional `data` payload (the `density` table travels there and appears in the JSON output). If an analyzer raises, it is reported as a warning and the others still run.

## Known limits

- Assumes 4/4 when converting beats to bars.
- Key detection reads names only; it cannot hear the audio. Chord names such as `Am7` are not recognised.
- Transposition is applied only to warped clips; fine-tune cents are ignored.
- If the `.als` was copied out of its `... Project` folder, the project folder is inferred from the sample paths.

## Development

```bash
pytest
```

Tests build minimal synthetic sessions (`tests/factory.py`); no real sessions are committed. To try your own, put them in `local_sessions/`, which is git-ignored because real sessions contain absolute paths from your machine.
