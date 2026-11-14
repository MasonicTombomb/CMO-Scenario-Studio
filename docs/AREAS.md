# Patrol area library

The area library holds **predefined sea and air patrol areas** - the operating areas scenarios use again and again,
such as the Bay of Biscay, the GIUK gaps, the Baltic, the Strait of Hormuz, the Taiwan Strait or the Falklands
exclusion zone - grouped by region of the globe. Adding one creates an ordinary area (reference points
`NAME-1`..`NAME-n`) and, if you like, a patrol or support mission on it.

The built-in library has **134 areas** (94 sea, 40 air): Europe 44, Arctic 10, Middle East 14, Africa 8, Asia 26, Oceania 9, North America 13, South America 10.

- **Sea areas** - ASW, ASuW and MCM patrol areas, chokepoints and barriers (GIUK, Bear Gap, Gibraltar, Hormuz,
  Bab-el-Mandeb, Malacca, Luzon Strait...), carrier operating areas, bastions and training areas.
- **Air areas** - CAP boxes and QRA areas (Baltic air policing, NORAD intercept zones, Korean DMZ, Taiwan ADIZ...),
  AEW orbits, tanker tracks and training ranges.

Shapes are approximate operating boxes drawn for gameplay, not legal or official boundaries. Adjust the corners on
the map after adding an area, or edit the library.

## Using it

- **Tools > Add patrol area from library** (Ctrl+Shift+A), the map toolbar's **Patrol areas...** button, the map's
  right-click menu, or **From library...** on the Areas tab. Ctrl+K search also finds library areas by name
  ("Biscay", "Hormuz").
- Filter by **region** (Europe, Arctic, Middle East, Africa, Asia, Oceania, North America, South America), by
  **sea / air**, or by search words (name, sub-region, description or tags such as `chokepoint`, `CAP`, `tanker`).
  The tree groups areas by region, then sea and air. The map preview shows the selected area among its neighbours;
  click an area on the preview to select it.
- Choose the **side**, the **area name** (exported as reference points `NAME-1`, `NAME-2`...; the default is the
  library id, e.g. `BISCAY`), whether the points go on **every side**, and whether to colour the area by kind (sea
  blue, air orange) instead of the side colour.
- **Create a mission on it** adds a mission with no units yet. *Suggested for each area* picks:

  | Area | Mission |
  | --- | --- |
  | air area tagged `AEW`, `tanker`, `AAR` or `orbit` | Support |
  | air area tagged `strike` or `ISR` but not `CAP` | Patrol - land |
  | other air areas | Patrol - AAW (named *... CAP*) |
  | sea area where `ASW` comes before `ASuW` in the tags | Patrol - ASW |
  | other sea areas | Patrol - ASuW (naval) |

  Or pick one mission type for all of them.
- Ctrl/Shift-click to add several areas at once; each becomes its own area (and mission). Everything added in one go
  is one undo step.
- **Save to area library...** (on an area's form, or right-click an area on the map) keeps an area you drew for
  other scenarios; the studio suggests a region from its position.

## Where the files are

| File | Purpose |
| --- | --- |
| `src/cmo_studio/data/areas.json` (in the exe: `_internal\cmo_studio\data\`) | The built-in areas. Replaced by updates. |
| `%APPDATA%\CMOScenarioStudio\CMO Scenario Studio\areas.json` | **Your library.** Written by *Save* in Tools > Area library or by *Save to area library*; used instead of the built-in file when present. |

**Tools > Area library** edits the library: add, duplicate and delete areas; change name, region, kind, sub-region,
tags and description; edit corners in the table or drag them on the map; import, export, show the file or reset to
the built-in areas. New regions can be typed straight into the region box.

## Format

```jsonc
{
  "format": "cmo-studio-areas",
  "version": 1,
  "regions": ["Europe", "Arctic", "Middle East", "Africa", "Asia", "Oceania", "North America", "South America"],
  "areas": [
    {
      "id": "biscay",                       // unique key; also the default area name (BISCAY)
      "name": "Bay of Biscay",
      "region": "Europe",                   // any string; new regions are added to the list
      "kind": "sea",                        // "sea" or "air"
      "subregion": "Atlantic approaches",
      "description": "The bay between Brittany and northern Spain...",
      "tags": ["ASW", "ASuW", "transit"],   // searchable; also choose the suggested mission
      "points": [[47.8, -5.0], [47.8, -2.6], [46.0, -1.6]]   // [latitude, longitude] corners in order
    }
  ]
}
```

## Built-in areas

### Europe

**Sea areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Bay of Biscay** (`biscay`) | Atlantic approaches | 311 x 264 | ASW Patrol | ASW, ASuW, transit |
| **Celtic Sea** (`celtic_sea`) | Atlantic approaches | 160 x 132 | ASW Patrol | ASW |
| **Western Approaches** (`western_approaches`) | Atlantic approaches | 233 x 210 | ASW Patrol | ASW, convoy |
| **Central Baltic** (`baltic_central`) | Baltic | 130 x 222 | ASW Patrol | ASW, ASuW |
| **Gulf of Bothnia** (`gulf_bothnia`) | Baltic | 191 x 318 | ASW Patrol | ASW |
| **Gulf of Finland** (`gulf_finland`) | Baltic | 226 x 60 | ASW Patrol | ASW, ASuW, MCM |
| **Gulf of Riga** (`gulf_riga`) | Baltic | 61 x 78 | ASuW Patrol | ASuW, MCM |
| **Southern Baltic (Bornholm)** (`baltic_south`) | Baltic | 227 x 102 | ASW Patrol | ASW, ASuW |
| **Skagerrak and Kattegat** (`skagerrak_kattegat`) | Baltic approaches | 161 x 180 | ASW Patrol | ASW, chokepoint |
| **Eastern Black Sea** (`black_sea_east`) | Black Sea | 337 x 204 | ASW Patrol | ASW, ASuW |
| **Western Black Sea** (`black_sea_west`) | Black Sea | 188 x 204 | ASW Patrol | ASW, ASuW |
| **Irish Sea** (`irish_sea`) | British Isles | 104 x 162 | ASW Patrol | ASW, transit |
| **Dover Strait and eastern Channel** (`channel_east`) | Channel | 103 x 66 | ASuW Patrol | ASuW, MCM, chokepoint |
| **English Channel (western)** (`channel_west`) | Channel | 155 x 102 | ASuW Patrol | ASuW, MCM, transit |
| **Adriatic Sea** (`adriatic`) | Mediterranean | 290 x 306 | ASuW Patrol | ASuW, embargo |
| **Aegean Sea** (`aegean`) | Mediterranean | 175 x 300 | ASW Patrol | ASW, ASuW |
| **Alboran Sea** (`alboran`) | Mediterranean | 170 x 90 | ASuW Patrol | ASuW, ASW |
| **Balearic Sea** (`balearic`) | Mediterranean | 359 x 240 | ASW Patrol | ASW, ASuW |
| **Eastern Mediterranean (Levant)** (`levant_basin`) | Mediterranean | 295 x 252 | ASW Patrol | ASW, ASuW, carrier ops |
| **Ionian Sea** (`ionian`) | Mediterranean | 223 x 228 | ASW Patrol | ASW, ASuW |
| **Strait of Gibraltar** (`gibraltar`) | Mediterranean | 58 x 24 | ASW Patrol | chokepoint, ASW, ASuW |
| **Strait of Sicily** (`sicily_strait`) | Mediterranean | 183 x 120 | ASuW Patrol | chokepoint, ASuW |
| **Tyrrhenian Sea** (`tyrrhenian`) | Mediterranean | 270 x 246 | ASW Patrol | ASW, ASuW |
| **Faroes-Shetland Channel** (`faroes_shetland`) | North Atlantic | 173 x 138 | ASW Patrol | ASW, chokepoint |
| **GIUK Gap - Denmark Strait** (`giuk_denmark_strait`) | North Atlantic | 232 x 144 | ASW Patrol | ASW, barrier, chokepoint |
| **GIUK Gap - Iceland-Faroes** (`giuk_iceland_faroes`) | North Atlantic | 228 x 192 | ASW Patrol | ASW, barrier, chokepoint |
| **Norwegian Sea** (`norwegian_sea`) | North Atlantic | 414 x 480 | ASW Patrol | ASW, carrier ops |
| **Central North Sea** (`north_sea_central`) | North Sea | 322 x 168 | ASW Patrol | ASW, ASuW |
| **Northern North Sea** (`north_sea_north`) | North Sea | 193 x 210 | ASW Patrol | ASW, ASuW, offshore |
| **Southern North Sea** (`north_sea_south`) | North Sea | 273 x 204 | ASuW Patrol | ASuW, MCM |

**Air areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Baltic tanker track** (`tanker_baltic`) | Baltic | 66 x 30 | Support | tanker, AAR |
| **AEW orbit - Poland** (`aew_poland_orbit`) | NATO eastern flank | 73 x 36 | Support | AEW, orbit |
| **AEW orbit - Romania** (`aew_romania_orbit`) | NATO eastern flank | 85 x 36 | Support | AEW, orbit |
| **Baltic air policing** (`cap_baltic_air_policing`) | NATO eastern flank | 231 x 234 | CAP | CAP, QRA |
| **Eastern Poland CAP** (`cap_poland_east`) | NATO eastern flank | 114 x 234 | CAP | CAP |
| **Kaliningrad watch** (`cap_kaliningrad`) | NATO eastern flank | 156 x 84 | CAP | CAP, ISR |
| **Romania / Black Sea CAP** (`cap_romania_black_sea`) | NATO eastern flank | 149 x 120 | CAP | CAP |
| **Eastern Finland CAP** (`cap_finland_east`) | Nordic | 95 x 228 | CAP | CAP |
| **Finnmark / northern Norway CAP** (`cap_finnmark`) | Nordic | 194 x 108 | CAP | CAP |
| **Iceland air policing** (`cap_iceland`) | North Atlantic | 267 x 192 | CAP | QRA, CAP |
| **North Sea QRA box** (`cap_north_sea_qra`) | North Sea | 133 x 120 | CAP | QRA, CAP |
| **North Sea tanker track** (`tanker_north_sea`) | North Sea | 89 x 30 | Support | tanker, AAR |
| **Aegean CAP** (`cap_aegean`) | Southern Europe | 117 x 120 | CAP | CAP |
| **Balkans CAP** (`cap_balkans`) | Southern Europe | 231 x 192 | CAP | CAP, no-fly |


### Arctic

**Sea areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Bear Gap (Svalbard-Norway)** (`bear_gap`) | Barents | 167 x 264 | ASW Patrol | ASW, barrier, chokepoint |
| **Kola approaches** (`barents_kola`) | Barents | 197 x 144 | ASW Patrol | ASW, SSBN, bastion |
| **Western Barents Sea** (`barents_west`) | Barents | 315 x 240 | ASW Patrol | ASW, SSBN |
| **Beaufort Sea** (`beaufort_sea`) | North American Arctic | 417 x 180 | ASW Patrol | ASW, ice edge |
| **Bering Strait** (`bering_strait`) | Pacific Arctic | 147 x 132 | ASW Patrol | chokepoint, ASW |
| **Kara Sea** (`kara_sea`) | Russian Arctic | 301 x 390 | ASW Patrol | ASW, NSR |
| **Svalbard waters** (`svalbard`) | Svalbard | 241 x 258 | ASW Patrol | ASW, ice edge |

**Air areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Kola Peninsula CAP** (`cap_kola`) | Barents | 154 x 126 | CAP | CAP |
| **Alaska NORAD intercept zone** (`cap_alaska_norad`) | North American Arctic | 338 x 480 | CAP | QRA, CAP, NORAD |
| **Canadian Arctic CAP** (`cap_canadian_arctic`) | North American Arctic | 409 x 240 | CAP | CAP, NORAD |


### Middle East

**Sea areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Gulf of Aden** (`gulf_aden`) | Arabian Sea | 445 x 222 | ASuW Patrol | ASuW, escort, piracy |
| **Gulf of Oman** (`gulf_oman`) | Arabian Sea | 247 x 180 | ASW Patrol | ASW, ASuW |
| **Northern Arabian Sea** (`arabian_sea_north`) | Arabian Sea | 533 x 390 | ASW Patrol | carrier ops, ASW |
| **Suez Canal northern approaches** (`suez_approaches`) | Mediterranean | 72 x 42 | ASuW Patrol | chokepoint |
| **Central Persian Gulf** (`gulf_central`) | Persian Gulf | 227 x 168 | ASuW Patrol | ASuW, MCM, carrier ops |
| **Northern Persian Gulf** (`gulf_north`) | Persian Gulf | 143 x 174 | ASuW Patrol | ASuW, MCM |
| **Strait of Hormuz** (`hormuz`) | Persian Gulf | 75 x 84 | ASuW Patrol | chokepoint, ASuW, MCM |
| **Bab-el-Mandeb and southern Red Sea** (`bab_el_mandeb`) | Red Sea | 209 x 246 | ASuW Patrol | chokepoint, ASuW, escort |
| **Northern Red Sea** (`red_sea_north`) | Red Sea | 273 x 360 | ASuW Patrol | ASuW |

**Air areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **AEW orbit - eastern Mediterranean** (`aew_east_med`) | Levant | 74 x 36 | Support | AEW, orbit |
| **Israel-Lebanon CAP** (`cap_levant`) | Levant | 55 x 66 | CAP | CAP |
| **Northern Iraq / Syria CAP** (`cap_northern_iraq_syria`) | Levant | 219 x 162 | CAP | CAP, strike |
| **Persian Gulf CAP** (`cap_gulf`) | Persian Gulf | 135 x 150 | CAP | CAP |
| **Red Sea CAP** (`cap_red_sea`) | Red Sea | 191 x 240 | CAP | CAP, escort |


### Africa

**Sea areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Mozambique Channel** (`mozambique_channel`) | East Africa | 569 x 781 | ASuW Patrol | ASuW, transit |
| **Somali Basin** (`somali_basin`) | Horn of Africa | 775 x 600 | ASuW Patrol | ASuW, piracy |
| **Gulf of Sidra** (`gulf_sidra`) | North Africa | 245 x 114 | ASuW Patrol | ASuW |
| **Cape of Good Hope** (`cape_good_hope`) | Southern Africa | 295 x 240 | ASuW Patrol | ASuW, transit |
| **Gulf of Guinea** (`gulf_guinea`) | West Africa | 540 x 348 | ASuW Patrol | ASuW, piracy, offshore |

**Air areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Horn of Africa ISR box** (`cap_horn`) | Horn of Africa | 390 x 360 | Land Patrol | ISR, strike |
| **Libya no-fly zone (central)** (`cap_libya`) | North Africa | 412 x 216 | CAP | CAP, no-fly |
| **Sahel CAP (Mali / Niger)** (`cap_sahel`) | West Africa | 348 x 240 | CAP | CAP, strike, ISR |


### Asia

**Sea areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **East China Sea** (`east_china_sea`) | East Asia | 366 x 324 | ASW Patrol | ASW, ASuW |
| **Luzon Strait / Bashi Channel** (`luzon_strait`) | East Asia | 140 x 138 | ASW Patrol | ASW, chokepoint |
| **Sea of Japan (central)** (`sea_of_japan`) | East Asia | 322 x 252 | ASW Patrol | ASW, BMD |
| **Sea of Okhotsk (bastion)** (`sea_of_okhotsk`) | East Asia | 262 x 420 | ASW Patrol | ASW, SSBN, bastion |
| **Senkaku / Diaoyu Islands** (`senkaku`) | East Asia | 119 x 84 | ASuW Patrol | ASuW, presence |
| **Taiwan Strait** (`taiwan_strait`) | East Asia | 225 x 216 | ASW Patrol | ASW, ASuW, chokepoint |
| **Tsushima / Korea Strait** (`tsushima`) | East Asia | 89 x 90 | ASW Patrol | chokepoint, ASW |
| **Yellow Sea** (`yellow_sea`) | East Asia | 231 x 246 | ASW Patrol | ASW, ASuW |
| **Andaman Sea** (`andaman_sea`) | South Asia | 236 x 480 | ASW Patrol | ASW |
| **Arabian Sea - Indian west coast** (`arabian_sea_india`) | South Asia | 392 x 480 | ASW Patrol | ASW, ASuW |
| **Bay of Bengal** (`bay_of_bengal`) | South Asia | 576 x 510 | ASW Patrol | ASW, ASuW |
| **Scarborough Shoal** (`scs_scarborough`) | South China Sea | 98 x 96 | ASuW Patrol | ASuW, presence |
| **South China Sea - Paracel Islands** (`scs_paracel`) | South China Sea | 155 x 150 | ASuW Patrol | ASuW, ASW |
| **South China Sea - Spratly Islands** (`scs_spratly`) | South China Sea | 296 x 270 | ASuW Patrol | ASuW, ASW, presence |
| **Lombok Strait** (`lombok_strait`) | South-East Asia | 36 x 48 | ASW Patrol | chokepoint, ASW |
| **Singapore Strait** (`singapore_strait`) | South-East Asia | 60 x 21 | ASuW Patrol | chokepoint |
| **Strait of Malacca** (`malacca`) | South-East Asia | 401 x 294 | ASuW Patrol | chokepoint, ASuW, piracy |
| **Sunda Strait** (`sunda_strait`) | South-East Asia | 72 x 72 | ASuW Patrol | chokepoint |
| **Philippine Sea** (`philippine_sea`) | Western Pacific | 677 x 600 | ASW Patrol | carrier ops, ASW |

**Air areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **East China Sea ADIZ** (`cap_ecs_adiz`) | East Asia | 158 x 240 | CAP | CAP, intercept |
| **Hokkaido / Kurils CAP** (`cap_hokkaido`) | East Asia | 259 x 180 | CAP | CAP, intercept |
| **Korean DMZ CAP** (`cap_korea_dmz`) | East Asia | 133 x 66 | CAP | CAP |
| **Okinawa CAP** (`cap_okinawa`) | East Asia | 134 x 120 | CAP | CAP |
| **Taiwan south-west ADIZ** (`cap_taiwan_sw_adiz`) | East Asia | 95 x 126 | CAP | CAP, intercept |
| **Kashmir / Punjab CAP** (`cap_kashmir`) | South Asia | 141 x 210 | CAP | CAP |
| **Ladakh LAC CAP** (`cap_ladakh`) | South Asia | 149 x 174 | CAP | CAP |


### Oceania

**Sea areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Hawaii operating area** (`hawaii_oparea`) | Central Pacific | 309 x 264 | ASW Patrol | ASW, training |
| **Timor Sea** (`timor_sea`) | Northern Australia | 365 x 210 | ASuW Patrol | ASuW, offshore |
| **Torres Strait and Arafura Sea** (`torres_arafura`) | Northern Australia | 443 x 156 | ASuW Patrol | chokepoint, ASuW |
| **Coral Sea** (`coral_sea`) | South Pacific | 488 x 600 | ASW Patrol | ASW, carrier ops |
| **Solomon Sea** (`solomon_sea`) | South Pacific | 327 x 300 | ASW Patrol | ASW |
| **Tasman Sea** (`tasman_sea`) | South Pacific | 761 x 540 | ASW Patrol | ASW |
| **Guam and the Marianas** (`guam_marianas`) | Western Pacific | 204 x 204 | ASW Patrol | ASW, carrier ops |

**Air areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Darwin CAP** (`cap_darwin`) | Northern Australia | 176 x 150 | CAP | CAP |
| **Guam CAP** (`cap_guam`) | Western Pacific | 93 x 96 | CAP | CAP |


### North America

**Sea areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Eastern Caribbean** (`caribbean_east`) | Caribbean | 406 x 384 | ASW Patrol | ASW, interdiction |
| **Florida Straits** (`florida_straits`) | Caribbean | 169 x 138 | ASW Patrol | chokepoint, ASW |
| **Gulf of Mexico (central)** (`gulf_mexico`) | Gulf of Mexico | 539 x 360 | ASW Patrol | ASW, offshore |
| **Grand Banks** (`grand_banks`) | North Atlantic | 252 x 240 | ASW Patrol | ASW, convoy |
| **Labrador Sea** (`labrador_sea`) | North Atlantic | 327 x 360 | ASW Patrol | ASW |
| **Virginia Capes operating area** (`vacapes`) | US Atlantic | 206 x 174 | ASW Patrol | ASW, training, carrier ops |
| **Gulf of Alaska** (`gulf_alaska`) | US Pacific | 460 x 330 | ASW Patrol | ASW, training |
| **Pacific Northwest approaches** (`pnw_approaches`) | US Pacific | 166 x 180 | ASW Patrol | ASW, SSBN |
| **Southern California operating area** (`socal_oparea`) | US Pacific | 157 x 120 | ASW Patrol | ASW, training, carrier ops |

**Air areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Gulf of Mexico tanker track** (`tanker_gulf_mexico`) | Gulf of Mexico | 106 x 30 | Support | tanker, AAR |
| **New York CAP** (`cap_new_york`) | Homeland defence | 55 x 54 | CAP | CAP, homeland |
| **Washington DC CAP** (`cap_washington`) | Homeland defence | 51 x 48 | CAP | CAP, homeland |
| **Nevada Test and Training Range** (`nttr`) | Training ranges | 77 x 72 | CAP | training |


### South America

**Sea areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Panama Canal - Caribbean entrance** (`panama_caribbean`) | Caribbean | 89 x 30 | ASuW Patrol | chokepoint |
| **Venezuelan coast (Caribbean)** (`venezuela_coast`) | Caribbean | 529 x 108 | ASuW Patrol | ASuW, interdiction |
| **Callao approaches (Peru)** (`callao_approaches`) | Eastern Pacific | 141 x 120 | ASW Patrol | ASW |
| **Panama Canal - Pacific entrance** (`panama_pacific`) | Eastern Pacific | 71 x 66 | ASuW Patrol | chokepoint |
| **Drake Passage** (`drake_passage`) | South Atlantic | 256 x 264 | ASuW Patrol | transit |
| **Falklands Total Exclusion Zone** (`falklands_tez`) | South Atlantic | 400 x 400 | ASW Patrol | ASW, ASuW, 1982 |
| **Río de la Plata approaches** (`rio_de_la_plata`) | South Atlantic | 146 x 120 | ASuW Patrol | ASuW |
| **Santos Basin (pre-salt)** (`santos_basin`) | South Atlantic | 354 x 240 | ASuW Patrol | ASuW, offshore |

**Air areas**

| Area | Sub-region | Size (nm) | Default mission | Tags |
| --- | --- | --- | --- | --- |
| **Venezuela-Guyana border CAP** (`cap_essequibo`) | Northern South America | 179 x 210 | CAP | CAP |
| **Falklands CAP (Mount Pleasant)** (`cap_falklands`) | South Atlantic | 156 x 108 | CAP | CAP |
