# About this manual {.unnumbered}

The **Reference Manual** is the technical companion to the *User Manual*. It is for advanced scenario designers,
modders, people who want to edit the libraries by hand or generate scenarios from code, and contributors. You never
need it to build ordinary scenarios: everything here can also be done with the studio's forms.

| Chapter | Covers |
| --- | --- |
| Files, command line and running from source | Where everything lives, headless export and dry-run, running the source code |
| Project file format | The `.cmoproj` JSON, and generating projects from Python |
| Export format and Lua runtime | Every exported file, the build order, the `D` data table and the `Studio...` runtime API |
| Events and the generated Lua | Exactly how triggers, conditions and actions become CMO events |
| Formation layouts | Every layout and its settings |
| Unit templates | The template library format, the UK real-world sites and the full catalogue |
| Patrol area library | The area library format and the full list of areas |
| Callsign library | The callsign library format, roles and allocation rules |
| Database access | Which DB3000 tables the studio reads and how |
| Importing builder scenarios | Bringing an existing *Build_Scenario.lua* into a project |
| Building, signing and releasing | The installer, updates and code signing |

The conventions are the same as in the User Manual: **bold** for on-screen controls, `code` for file names and
things you type, and [[Ctrl+S]] for keys.
