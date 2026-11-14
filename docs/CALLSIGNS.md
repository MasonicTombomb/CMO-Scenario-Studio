# Callsign library

The studio names aircraft from a **callsign library**: a standalone JSON file listing, per country, the squadrons
that fly each role and the callsign words they use. Words become flights of numbered aircraft:

```
TARTAN 11  TARTAN 12  TARTAN 13  TARTAN 14      flight 1 of TARTAN (4-ship)
TARTAN 21  TARTAN 22 ...                        flight 2
```

## Where the files are

| File | Purpose |
| --- | --- |
| `src/cmo_studio/data/callsigns.json` (inside the exe's `_internal\cmo_studio\data\`) | The built-in default. Do not edit; it is replaced by updates. |
| `%APPDATA%\CMOScenarioStudio\CMO Scenario Studio\callsigns.json` | **Your library.** Created when you press *Save* in Tools > Callsign library (or *Show file*). When it exists and is valid it is used instead of the default. |

Edit your library in the studio (Tools > Callsign library) or with any text editor. *Import...* / *Export...* share
libraries between people; *Reset to defaults* starts again from the built-in one.

The default covers 38 entries (the major NATO air arms, Russia, China, India, Iran, Israel, Japan, the Koreas,
Australia, Pakistan, Saudi Arabia, Ukraine, Egypt, Brazil, Taiwan, the Baltic states, NATO's own units and a Generic
fallback) with about 365 squadrons and 1,100 callsign words. Squadron names, bases and aircraft are a realistic
starting point; **callsign words are illustrative, in each air arm's style, not a list of real assignments.** Rename
anything you like.

## Format

```jsonc
{
  "format": "cmo-studio-callsigns",
  "version": 1,
  "roles": { "FIGHTER": "Fighter / air defence", "AEW": "Airborne early warning / C2", ... },
  "fallbacks": { "ATTACK": ["STRIKE", "FIGHTER"], "TANKER": ["TRANSPORT"], ... },
  "default_format": "{word} {flight}{member}",
  "default_flight_size": 4,
  "max_flights_per_word": 9,
  "countries": [
    {
      "name": "United Kingdom",
      "match": ["United Kingdom"],            // prefixes of the database operator country
      "format": "{word} {flight}{member}",    // how names are built
      "flight_size": 4,                       // aircraft per flight
      "notes": "",
      "squadrons": [
        {
          "name": "617 Squadron",
          "service": "RAF",
          "base": "RAF Marham",
          "aircraft": "F-35B",
          "roles": ["STRIKE", "SEAD", "FIGHTER", "ASUW"],
          "callsigns": ["DAMBUSTER", "UPKEEP", "GIBSON"]
        }
      ]
    }
  ]
}
```

### Roles

| Key | Used for |
| --- | --- |
| `FIGHTER` | fighters and multirole aircraft on air-to-air loadouts |
| `STRIKE` | strike / interdiction loadouts |
| `ATTACK` | close air support, attack aircraft |
| `SEAD` | anti-radiation / suppression loadouts, Wild Weasels |
| `ASUW` | anti-ship (naval strike) loadouts |
| `BOMBER` | bombers |
| `AEW` | AEW and airborne command posts |
| `EW` | electronic warfare / offensive ECM |
| `ISR` | reconnaissance, ELINT, SIGINT |
| `MPA` | maritime patrol and ASW aircraft |
| `TANKER` | tankers |
| `TRANSPORT` | airlifters, cargo and paratroop loadouts |
| `ASW_HELO` | naval helicopters |
| `ATTACK_HELO` | attack helicopters |
| `UTILITY_HELO` | transport / utility helicopters |
| `CSAR` | search and rescue, combat SAR |
| `UAV` | drones |
| `TRAINER` | trainers and aggressors |

The role of an aircraft is detected from its database **type** (fighter, AEW, tanker...), its **category**
(helicopters get the `_HELO` roles) and its current **loadout role** (an F-16 with HARMs is `SEAD`, with Harpoons
`ASUW`). If a country has no squadron for a role, the `fallbacks` chain is tried, then the `Generic` entry.

### Countries

`match` is compared with the start of the aircraft's operator country in the database, ignoring case: `"Russia"`
matches `Russia [1992-]`, and `"Germany [FRG"` matches the reunified Germany but not the DDR. The longest match
wins. Several countries can share an entry (the default *Baltic States* matches Estonia, Latvia and Lithuania).
Aircraft whose country matches nothing use `Generic`.

### Name format

`format` may use `{word}`, `{flight}`, `{member}` and `{squadron}`. Numbers accept Python format specs:

| Format | Names |
| --- | --- |
| `{word} {flight}{member}` | TARTAN 11, TARTAN 12 |
| `{word}-{flight}{member}` | SOKOL-11, SOKOL-12 |
| `{word}{flight}{member:02d}` | HAWK101, HAWK102 |
| `{word} {flight}-{member}` | VIPER 1-1, VIPER 1-2 |

A counted unit that is not split into single aircraft gets the flight callsign (the format without the member
number, e.g. `TARTAN 1`), and the build script adds `#1`, `#2`...

## Allocation rules

- Each unit starts a new flight; flights are never shared between units.
- With the squadron left on *automatic*, successive units of the same country and role come from successive
  squadrons; choose a squadron per row to override.
- Any flight with a name already used in the project is skipped, so assigning again never duplicates callsigns.
- When a squadron's words run out the next squadron is used; if the whole library is exhausted, names fall back to
  `ROLE n`.
