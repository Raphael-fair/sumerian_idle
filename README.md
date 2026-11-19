# Sumerian Idle: Legacy of Uruk

Phase 1 playable foundation. Python/Kivy, portrait-first Android design.

## Windows development

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install kivy
python main.py
python -m unittest discover -s tests -v
```

## Android packaging

Use WSL2 Ubuntu or a Linux build machine with Android SDK/NDK and Buildozer.
Install Buildozer, initialize its spec, set source directory, package metadata and orientation using `config/build.json`, then run `buildozer android debug`. A native Windows Buildozer build is not supported. Android packaging has not been verified in Phase 1.

## Phase 1 features

- Responsive Kivy layout in density-independent units with scrolling, minimum touch targets, and portrait desktop preview.
- Barley harvesting, three resource producers, building construction with scaling costs.
- Seven demonstrator achievements with one-time rewards.
- Atomic JSON save and offline progression capped at eight hours.
- Headless engine tests.

## Next milestone

Phase 2: coherent pixel-art/SVG asset pipeline, genuinely illustrated layered 2D settlement, visual treatments, and animation groundwork. Current Phase 1 cards are intentional placeholders.

## Phase 2: 2D art foundation

- Original rounded vector artwork: `data/art/svg/`.
- Matching runtime PNG textures: `data/art/png/`.
- JSON-defined layered settlement: `config/art.json`.
- Responsive portrait-scrolling scene with fixed artwork aspect ratio and clamped height.
- Farm, clay pit and reed garden appear when constructed; house and ziggurat are scenic placeholders until later gameplay phases.
- Kivy loads PNG files directly; SVG source files can be edited and re-exported offline.
- Build scripts must include `png`, `svg` and `json` files in the package.

Run checks with `python -m unittest discover -s tests -v`.
Kivy rendering and Android APK builds have not been verified in this environment.

## Phase 3: panoramic interactive world

- Three-tile panoramic world with horizontal touch scrolling, separate from vertical interface scrolling.
- Tap the farm, residences, ziggurat, clay pit, or reed garden to inspect them.
- Building visibility follows actual construction levels.
- Idle breeze, temple glow and clay shimmer run at a capped frame rate; animation parameters are JSON-driven.
- Camera position is preserved across UI refreshes and building interactions.
- HUD resource totals update without rebuilding the world every simulation tick.
- All gameplay data and visual parameters remain in JSON; only one root `main.py` entry point.

Android device performance and Kivy graphics execution are not yet verified. Kivy is not installed in the headless test environment.

## Phase 4: Production chains and offline economy

- Five resources: barley, clay, reeds, bricks, and bread.
- Six structures: farms, clay pits, reed gardens, brick kilns, bakeries, and granaries.
- Brick kilns consume clay and reeds; bakeries consume barley. No output appears without required inputs.
- Resource storage limits, expandable with granaries, prevent infinite unattended accumulation.
- Offline production runs for at most the configured cap and reports resources gained on return.
- Eight additional achievement milestones track crafting, consumption, granaries, and offline progress.
- Existing version-one saves migrate naturally via default resources and building counts.
- All economy rates, prices, recipes, capacities, limits, and rewards remain JSON-configured.

Run `python -m unittest discover -s tests -v`. Game rendering and Android APK packaging still require Kivy and an Android build environment.

## Phase 5: Citizens and professions

- Housing capacity grows with mudbrick homes; settlement begins with eight citizens.
- Citizen growth consumes bread and barley. Household feeding consumes bread on a separate timer.
- Workers automatically staff available production buildings; the People tab pins individual staffing levels.
- Unstaffed workshops halt production. Worker assignment and population timers persist in JSON saves.
- Up to twelve citizens walk through the settlement as lightweight canvas figures; movement and styling are JSON-configured.
- Six new achievements reward housing, staffing, feeding, and births, bringing the archive to 21.
- Version-one saves from earlier phases remain readable. Headless game logic is tested, but Kivy visual rendering and Android packaging remain unverified.

## Phase 6: Legacy Archive

- 69 achievements across harvest, economy, construction, crafting, citizens, legacy and hidden secrets.
- Achievement tiers award legacy points and unlock collectible seals.
- Six themed collections grant one-time cosmetic relic rewards when all requirements are met.
- The Legacy screen has category filters, secret masking, collection progress and incremental achievement loading.
- Collection and relic ownership persist in the existing version-one save format, compatible with older saves.
- Cosmetic rewards currently exist as collected inventory IDs; placement and visible world decoration will follow in later phases.
- No APK or Kivy runtime rendering verification in this environment.

## Phase 7: Research, expeditions, and artifacts

- Ten interconnected research projects with prerequisites, resource costs, and permanent production bonuses.
- Five repeatable timed expeditions, each with upfront costs, resource rewards, and a unique first-discovery artifact.
- Five persistent artifacts, twelve additional achievements, and two secret discoveries, bringing the archive to 81 achievements.
- Discover tab includes Research, Explore, and Artifacts panels in the portrait-first UI.
- Expeditions advance during active play and capped offline progression; no parallel expedition stacking.
- Older version-one saves migrate using optional new fields without resetting existing progress.
- Run `python -m unittest discover -s tests -v`. Android APK packaging and Kivy rendering remain unverified.

## Phase 8: Civilization progression

- Five successive eras with research, building, and resource requirements.
- Four one-time monuments with persistent production upgrades.
- Five royal commissions with objective tracking, material payments, resource rewards, and renown.
- Royal renown produces legacy ranks and cumulative production bonuses.
- Thirteen additional achievements, now 94 total.
- Civilization interface lives inside the Legacy tab alongside achievement archives.
- All progress persists in compatible version-one JSON saves; old saves begin at the initial era.
- Android APK compilation and real-device layout verification remain outstanding.

## Phase 9: Animation, audio, balancing and stability

- Day/night tint, floating ambient motes, and capped achievement/building sparkle effects are configured in `config/art.json`.
- Five original, synthesized WAV interaction sounds (tap, build, achievement, error, research) are controlled by `config/gui.json`.
- Toast notifications have configurable lifetimes, and the game autosaves during active play.
- Corrected a serious Phase 8 expedition completion bug that erased civilization eras, monuments, and royal progress.
- Added VFX, audio integrity, persistence, and long-run economy regression tests.
- Kivy rendering and audio playback require manual device verification; Android APK is not compiled here.

## Phase 10: Android release preparation

- Adaptive city card columns (single-column on narrow devices), shorter UI chrome on compact-height viewports, and compact navigation labels.
- Generated Buildozer specification from `config/build.json`. No release metadata is hardcoded in a Python module.
- On Android, saves use the private app storage directory rather than a potentially unwritable home directory.
- Android configuration targets portrait orientation, API 35, minimum API 23, and ARM64/ARMv7 architectures.
- The Android source package includes Python, JSON, SVG, PNG, and WAV game assets and excludes tests, bytecode, virtual environments, and Git data.
- Android system bars remain visible (`fullscreen = 0`) to avoid overlapping cutouts and navigation regions on most devices. Edge-to-edge insets and real handset layouts still need verification.
- Source, asset, layout, packaging, persistence, and gameplay checks: 58 automated tests.

### Windows-first development

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install kivy
py main.py
py -m unittest discover -s tests -v
py main.py --prepare-android
```

### Build APK using WSL2 Ubuntu

From the project directory mounted in WSL2, preferably copied into the WSL Linux filesystem:

```sh
python3 -m pip install --user buildozer
python3 main.py --prepare-android
buildozer android debug
```

Buildozer additionally requires the supported Java JDK, C compiler, development headers, Android SDK/NDK, and other host prerequisites. Follow the current Buildozer installation guide for the WSL2 Ubuntu version in use. Android dependencies/downloads are not bundled in this ZIP. The generated APK, if the build succeeds, appears under `bin/`.

### Pre-release manual acceptance checks

1. Install a debug APK on a real small Android phone (approximately 320dp wide) and a modern phone with display cutouts.
2. Verify that title, resources, world scrolling, navigation, construction buttons, and achievement/archive screens remain reachable.
3. Verify sound playback, animation smoothness, battery drain, rotation policy, and switching apps.
4. Verify saves persist after app termination and that older Phase 9 saves migrate correctly.
5. Verify ARM64 APK installation and run a longer idle-economy balance session.

**Release status:** Source package ready for a debug-build attempt. Actual Buildozer APK compilation, Android execution, device visual QA, and production signing have not been performed.
