# Installing the studio

## Download

1. Open your web browser and go to
   **github.com/MasonicTombomb/CMO-Scenario-Studio/releases**.
2. The newest release is at the top. Under **Assets**, click **CMO-Scenario-Studio-*version*-setup.exe** to
   download the installer. (Click **Assets** first if the list is folded away.)
3. Wait for the download to finish. It is about 30 MB.

!!! note "Installer or zip?"
    Each release also has a **...-win64.zip**. That is the *portable* version: the same program in a folder you
    can unzip anywhere, for example onto a USB stick. It works exactly the same but cannot update itself. Use the
    installer unless you have a reason not to.

## Run the installer

1. Open your **Downloads** folder and double-click **CMO-Scenario-Studio-*version*-setup.exe**.
2. **If Windows shows a blue box saying "Windows protected your PC"**: this is Windows SmartScreen. It appears for
   programs that are new or not yet code-signed. Click **More info**, check the app name reads
   *CMO-Scenario-Studio-...-setup.exe*, then click **Run anyway**.
3. Windows asks *"Do you want to allow this app to make changes to your device?"* Click **Yes**. The studio
   installs into *Program Files*, which needs administrator permission, just like any other program.
4. **License Agreement**: the studio is free software under the MIT License. Select **I accept the agreement**
   and click **Next**.
5. **Select Destination Location**: leave it as `C:\Program Files\CMO Scenario Studio` and click **Next**.
6. **Select Additional Tasks**:
    - **Create a desktop shortcut**: tick it if you want an icon on your desktop.
    - **Open .cmoproj project files with CMO Scenario Studio**: leave this ticked so you can open projects by
     double-clicking them.

   Click **Next**, then **Install**.
7. When it finishes, leave **Launch CMO Scenario Studio** ticked and click **Finish**.

The studio is now in your Start menu under **CMO Scenario Studio**, with shortcuts to the program, the manuals,
the example projects and the uninstaller.

## The first start

When the studio starts for the first time it looks for CMO in your Steam libraries.

- **If it finds CMO**, the main window opens with an empty scenario and the **Database** panel on the right
  lists CMO's databases. You are ready to go.
- **If it cannot find CMO**, a message says *"Welcome! The CMO install folder was not found automatically."*
  Click **OK** and the **Settings** window opens so you can show it where CMO is.

![The Settings window](img/dialog_settings.png)

1. **CMO folder**: the folder that contains `Command.exe` and the `DB`, `Lua` and `Scenarios` folders. For Steam
   this is usually `C:\Program Files (x86)\Steam\steamapps\common\Command - Modern Operations`, or the same path
   inside another Steam library such as `D:\SteamLibrary\...`.
2. **Browse...** opens a folder picker so you can point at the CMO folder.
3. **Detect** searches your Steam libraries again.
4. **Autosave**: how often the studio saves a safety copy of your project (Chapter 3).
5. **Custom map tiles**: leave empty unless you have your own map server (Chapter 8).
6. **Check GitHub for a new version when the studio starts**: keep this ticked to be told about updates.

Under the folder box the studio says *"OK - N database file(s) found."* when the folder is right. Click **OK**.

!!! tip "Finding your CMO folder"
    In Steam, right-click **Command: Modern Operations** in your library, choose **Manage > Browse local files**.
    The folder that opens is the one you want. Click in Windows Explorer's address bar to copy its path.

## Updating

The installed studio keeps itself up to date:

1. A few seconds after it starts, it asks GitHub whether there is a newer release. (You can turn this off in
   **File > Settings...**.) You can also check at any time with **Help > Check for updates...**.
2. If there is one, a window shows what is new.

![An update is available](img/dialog_update.png)

    1. **Download and install** downloads the new installer, checks it has not been damaged or tampered with (it
      compares the file's SHA-256 fingerprint with the one published on GitHub) and asks before installing.
    2. **Skip this version** stops reminding you about this particular version.
    3. **Later** reminds you next time you start the studio.
3. If you choose to install, the studio asks you to save your work, closes, and the installer runs. Windows asks
   for permission (click **Yes**). The new version then starts by itself.

Your projects, settings and your own libraries are never touched by updating.

!!! note "Portable copies"
    The zip version cannot update itself. **Check for updates** opens the release page so you can download the new
    zip.

## Where your files are

| What | Where | Touched by updates? |
| --- | --- | --- |
| The program, its built-in libraries, the manuals and example projects | `C:\Program Files\CMO Scenario Studio` | Replaced by each update |
| Your projects (`.cmoproj`) | Wherever you save them (*Documents* by default) | Never |
| Your own template, area and callsign libraries, export backups, error log | `%APPDATA%\CMOScenarioStudio\CMO Scenario Studio` | Never |
| Settings (CMO folder, recent files, window layout) | The Windows registry, under your user | Never |
| Cached map pictures | `%LOCALAPPDATA%\CMOScenarioStudio\CMO Scenario Studio\cache` | Never |
| Exported scenarios | Your CMO folder: `Lua\<Scenario>\` and `Scenarios\<Scenario>\` | Never |

!!! tip "Opening %APPDATA%"
    Press [[Windows+R]], type `%APPDATA%\CMOScenarioStudio` and press [[Enter]]. The same works for `%LOCALAPPDATA%`.

## Uninstalling

Open Windows **Settings > Apps > Installed apps**, find **CMO Scenario Studio**, click the **...** button and
choose **Uninstall**. Or use **Uninstall CMO Scenario Studio** in the Start menu. Your projects, libraries and
settings are kept, in case you reinstall.
