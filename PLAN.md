# hdmi-ddc-input-switch — Implementation Plan

Companion to [hdmi-ddc-input-switch-brief.md](hdmi-ddc-input-switch-brief.md). Where this plan and the brief disagree, **this plan wins** (see Decisions).

## Decisions

| # | Decision | Replaces in brief |
|---|---|---|
| D1 | **Runtime configuration**, stored in flash, edited from a web configurator over Web Serial. One firmware build for everyone. | Compile-time profile selection |
| D2 | Monitor "profiles" become **presets** in `web/presets.json`. Adding a monitor = adding a preset. | Profiles in C++ |
| D3 | Invalid config (a button pointing at an input that doesn't exist, bad pin) is **rejected**: the firmware refuses it and the web page blocks the save. | `static_assert` |
| D4 | **Always output video** on the Feather's HDMI port: a simple text info screen. Compile flag exists only to turn it *off* for debugging. | Conditional DVI keep-alive, "status page out of scope" |
| D5 | No special "Info" button. The info screen is just the input the Feather is plugged into (e.g. HDMI 2); the user maps a normal button to it and labels the keycap. No toggle-back. | — |
| D6 | **Button count is configurable** (1–8 in firmware, limited by free pins); the case is parametric in the same count. | Fixed 2–4 |
| D6a | Buttons have an **action**: switch input, send an arbitrary VCP set command (e.g. a brightness preset), or none. Lets a button whose input is unused (HDMI 1 today) do something else. The onboard **BOOT button is readable as GPIO7** (isolated by diode D3 per the schematic), so it can be an extra configurable button, reachable through a pinhole in the lid (e.g. long-press = factory reset). RESET (SW1) is hardwired to RUN and can't be repurposed. | "Brightness/contrast out of scope" (only as a generic VCP action; no dedicated UI) |
| D7 | No unit-test environment. Verification is on hardware via the serial protocol. | — |
| D8 | Install via **UF2 + web page** (1200-baud touch → BOOTSEL drive → save `.uf2`). No WebUSB/PICOBOOT for v1 (Windows driver issue). | — |
| D9 | Case designed in **FreeCAD 1.1** as a parametric Python script, driven via the `freecad` MCP server (`.mcp.json`). | — |

## Architecture

### Repository layout

```
platformio.ini
src/
  main.cpp          setup/loop: buttons, serial, screen refresh
  config.h/.cpp     Config struct, defaults, validate(), load/save (EEPROM emu + CRC)
  ddc.h/.cpp        buildPacket(), ddcSend(), scanBus()   (transport kept separate — see Future)
  buttons.h/.cpp    debounce, edge detect
  protocol.h/.cpp   JSON-lines + single-char bench commands
  screen.h/.cpp     PicoDVI text-mode info screen (#ifndef DISABLE_VIDEO)
web/
  index.html        Install + Configure tabs (static, GitHub Pages)
  presets.json      monitor presets
case/
  case.py           parametric FreeCAD script (source of truth)
  export/           generated STL/3MF (built from case.py)
.github/workflows/
  build.yml         build .uf2 on push; attach to Release on tag
  pages.yml         deploy web/ (+ latest .uf2) to GitHub Pages
```

### Config model (firmware)

```cpp
struct InputDef  { char name[12]; uint8_t value; };
enum class Action : uint8_t { None, Input, Vcp };
struct ButtonDef {
  uint8_t pin;
  Action  action;
  uint8_t inputIndex;             // Action::Input
  uint8_t vcpCode, vcpSrc;        // Action::Vcp — any VCP set, e.g. a brightness preset (0x10) or picture mode
  uint16_t vcpValue;
};

struct Config {
  uint16_t  magic, schema;        // schema bumps on layout change → defaults
  char      presetName[24];
  uint8_t   vcpCode;              // 0xF4 LG / 0x60 MCCS
  uint8_t   sourceAddr;           // 0x50 LG / 0x51 MCCS
  uint8_t   numInputs;  InputDef  inputs[8];
  uint8_t   selfInput;            // index of the input the Feather is plugged into (0xFF = unknown)
  uint8_t   numButtons; ButtonDef buttons[8];
  uint32_t  crc;
};
```

- **Defaults** (empty/corrupt flash or schema mismatch): LG UltraGear; inputs DP `0xD0`, USB-C `0xD1`, HDMI 1 `0x90`, HDMI 2 `0x91`; self = HDMI 2; buttons left to right (as on the printed keycaps) A0→HDMI 1, A1→HDMI 2, A2→DP, A3→USB-C.
- **validate()**: `numInputs ≤ 8`, `numButtons ≤ 8`, each `Action::Input` button's `inputIndex < numInputs`, each pin in the allowed list and unique, names non-empty.
- **Allowed pins** (from schematic): A0–A3 (GPIO26–29), D24, D25, D5, D6, D9, D10, D11, D12, D13 (has red LED + resistor; usable with pull-up, LED glows faintly), MISO/MOSI/SCK, RX/TX, and BOOT (GPIO7). Excluded: SDA/SCL (GPIO2/3, DDC), GPIO4 (NeoPixel), GPIO16–23 (DVI).
- **Storage**: earlephilhower `EEPROM` emulation (one flash sector). A flash write stalls both cores, so video will glitch on save — accepted, documented.
- **Factory reset**: hold the first two buttons at power-up (or `{"cmd":"reset"}`).
- Packet + checksum are generic: `[src, 0x84, 0x03, vcp, 0x00, value, xor(0x6E, …)]`. Known-good: LG DP → checksum `0x9D`; MCCS DP1 `0x0F` → `0xD7`.

### Serial protocol (115200, newline-terminated)

Lines starting with `{` are JSON (ArduinoJson); otherwise single-char bench commands.

| Request | Response |
|---|---|
| `{"cmd":"version"}` | `{"fw":"1.0.0","schema":1,"board":"feather_dvi"}` |
| `{"cmd":"get"}` | full config as JSON (`pin` as Feather labels like `"A0"`, `self` = input index or -1) |
| `{"cmd":"set","config":{…}}` | `{"ok":true}` or `{"ok":false,"error":"button 2: input 5 out of range"}` — applies to RAM only |
| `{"cmd":"save"}` | writes flash |
| `{"cmd":"send","input":2}` | `{"ok":true,"ack":true}` |
| `{"cmd":"raw","vcp":244,"src":80,"value":208}` | ack — for discovering values on new monitors |
| `{"cmd":"scan"}` | `{"devices":[55,80]}` |
| `{"cmd":"reset"}` / `{"cmd":"reboot"}` / `{"cmd":"bootloader"}` | |
| `1`–`8` `s` `?` | bench shortcuts: send input slot 1–8, scan, help (human-readable) |

Unsolicited events (button presses, boot scan) are emitted as `{"event":…}` lines so the web page can show live activity.

### Info screen

PicoDVI 80-column text mode (`DVI_RES_640x240p60`); fallback 1-bit 640×480 or 8-bit 320×240 if the monitor rejects it. Runs on core 1. Call `Wire.setClock(50000)` **after** video starts (PicoDVI changes the system clock).

```
 HDMI-DDC INPUT SWITCH  v1.0.0          Preset: LG UltraGear (VCP F4 / src 50)
 You are viewing HDMI 2 - the switch's own port.

 Buttons:  [1] DP   [2] USB-C   [3] HDMI 1   [4] HDMI 2
 DDC:      0x37 OK   EDID 0x50 OK
 Last:     USB-C (0xD1) ACK   12s ago
 Configure: https://jeyeager65.github.io/hdmi-ddc-input-switch/
```

### Web page

Single static page, Chrome/Edge only (Web Serial). No build step.

- **Install tab**: pick port → open at 1200 baud and close (core reboots to BOOTSEL) → fetch latest `.uf2` → `showSaveFilePicker` onto the `RPI-RP2` drive. Fallback text: hold BOOT, tap RESET, drag the file.
- **Configure tab**: connect → `version` (warn on schema mismatch) → `get` → form:
  - preset dropdown (from `presets.json`) or Custom: VCP code, source address
  - input table: name, value, **Try** button (`send`/`raw`), "this is the switch's own port" radio
  - button table: pin dropdown (allowed pins only), input dropdown; add/remove rows
  - client-side validation mirrors firmware → **Save** (`set` then `save`)
  - live event log
- **presets.json** entry: `{ "id", "name", "vcp", "src", "inputs":[{"name","value"}], "notes" }`. Ship `lg-ultragear` and `mccs-standard` (DP1 0x0F, DP2 0x10, HDMI1 0x11, HDMI2 0x12; USB-C omitted — vendor-specific, e.g. Dell 0x1B).

### Case (FreeCAD)

**Decided (2026-10-03):** board centred behind the key row, fully inside the walls; the back section's side walls are thinned to 1.6 mm and the overhanging receptacle shells poke into tight holes (+0.25 mm), so plugs seat within ~1 mm of full insertion; lid is a flat plate mounted at 8° (keys centred in the front section); prints without supports (one-layer bridge capping each screw counterbore, no foot recesses — bumpers stick to the flat bottom); heat-set inserts (M2.5 for the Feather, M3 for the lid: 2 screws up through the floor at the front, 2 through the back wall); switches in a separate flat plate glued under a window in the lid (keytops 10.4 mm above the lid); RST/BOOT are real buttons: printed PLA plunger pins (rounded rectangles 4.4 × 3.6 mm with inlaid R / B, flush with the lid) resting on the board's buttons with a level-cut tip, guided by a sleeve on the switch plate's tab and trapped by a collar between the lid and that tab (0.4 mm press travel, 0.2 mm lift); no RST/BOOT text on the lid; lid art: an ultrawide monitor inlay (`LID_ART`); 4 keys; multi-colour printed keycaps.

Built: `case/coupon.py` (switch-fit coupon), `case/case.py` (tray + lid + switch plate, 94 × 65.5 mm, 14.3 mm high at the front / 23.5 mm at the back, 4 keys; board fully in the back section; tight port holes with a shallow recess for the plug housing; slots open at the top so the board drops in, closed by lid tabs. Changed after the first tray print trapped the board and blocked the plugs, 2026-10-04. R/B pins: 4.4 × 5.0 mm tops, letters styled like the keycap legends (Arial Narrow Bold 3.76 mm, strokes +0.12 mm), looser tip guides), `case/assembly.py` (preview with switches and keycaps, plus fit checks), shared helpers in `case/cadlib.py`. Board geometry is from Adafruit's Eagle files; connector heights, overhangs and RST/BOOT button height measured on the real board (2026-10-03). Switch cutout 14.0 mm and keycap stem cross 1.30 mm confirmed by test prints.

Keycaps: `case/keycaps.py` — low flat-top MX caps printed face-down with a flush two-colour legend (0.6 mm inlay, separate 3MF part), Arial Narrow Bold at one shared size; the top sits just above the stem and a deep skirt hides the switch and stops travel at 3 mm (Browns actuate at ~2 mm). Order left to right: HDMI 1, HDMI 2, DP, USB-C. Also a stem-fit test strip (cross widths 1.20–1.40 mm).

Colours (all PLA, "stealth"): tray black; lid gray with a black monitor frame and blue screen inlay; keycaps black with yellow legends; R/B buttons black with yellow letters; switch plate black (hidden). Filament is assigned per part in Bambu Studio.

Hardware: 4× M2.5×4×3.5 OD heat-set insert + 4× M2.5×6 screw (board, 3 mm standoffs so solder joints underneath need no trimming); 4× M3×4×5 OD heat-set insert (4.2 mm hole) + 4× M3×6 button-head screw (lid: 2 up through the floor at the front, 2 horizontally through the back wall); 4× adhesive bumper (any size, clear of the front screw holes); superglue for the switch plate (drop the two button pins in first; the plate's tab traps them).

Original parameter notes:

- `NUM_KEYS`, `KEY_PITCH = 19.05`, `SWITCH_CUTOUT = 14.0` (+ print tolerance), `PLATE_T = 1.5`
- Feather footprint 50.8 × 22.8 mm; connector positions from Adafruit's PCB files / STEP (don't guess)
- Openings for HDMI and USB-C; pinhole for RESET/BOOT
- Weight/feet allowance — HDMI cable stiffness will drag a light box
- Assembly: heat-set inserts (M2/M3) vs snap-fit — decide in Phase 8
- Optional: parametric keycap with embossed/debossed legend (e.g. "HDMI 2")
- First print a **switch-plate test coupon** to tune cutout tolerance

Workflow: Claude edits `case.py` → runs it via the MCP → reviews screenshots → exports STL/3MF to `case/export/`.

## Phases

| # | Phase | Done when |
|---|---|---|
| 0 | `git init`, `.gitignore`, `platformio.ini`; confirm board resolves; confirm `Wire` (not `Wire1`) reaches the DDC lines; confirm DVI + allowed pin list from schematic | Blink + serial echo uploads |
| 1 | Port reference code as-is (LG, one file) | Boot scan shows `0x37` and `0x50`; `d`/`c`/`1` switch the monitor |
| 2 | Add video + info screen | Picture on HDMI 2; DDC still ACKs; inactive-input switching works (bench test from brief) |
| 3 | Config model, flash storage, validation, JSON protocol | `get`/`set`/`save` round-trip survives reboot; bad config rejected |
| 4 | Buttons from config, debounce, factory-reset combo | One switch per press, no repeat; reset combo restores defaults |
| 5 | Hardening: one retry on NACK, 50 ms inter-command gap, pin platform commit, version string from git tag | Survives monitor power cycle without Feather reset |
| 6 | CI: build `.uf2`, attach to Release on tag | Tag → Release has `hdmi-ddc-input-switch-<ver>.uf2` |
| 7 | Web page + presets + Pages deploy | Fresh board → installed and configured entirely from the page |
| 8 | Case (can run in parallel after Phase 0 dims) | Coupon fits switches; full case printed and assembled |
| 9 | README: wiring, install, configure, adding a preset, safety notes | — |

## Progress

- **2026-10-03 — Phase 0 done:** git repo, `platformio.ini` (maxgerhardt platform, earlephilhower core, `adafruit_feather_dvi` resolves), firmware builds. Upload: picotool can't reach BOOTSEL on Windows without a Zadig driver, so flash by copying `.pio/build/feather_dvi/firmware.uf2` to the RPI-RP2 drive (the web installer plan already assumes this).
- **2026-10-03 — Phase 1 done:** reference code ported (4 keys: A0 HDMI 1, A1 HDMI 2, A2 DP, A3 USB-C). On the LG 45GR75DC-B via HDMI 2: I²C scan shows 0x37 + 0x50 (plus 0x30, 0x3A, 0x49, 0x4A, 0x51, 0x54, 0x59); `Wire` on GPIO2/3 is correct; VCP 0xF4 / src 0x50 switched DP → USB-C → DP with ACKs. **DDC is accepted on HDMI 2 while another input is displayed — no video keep-alive needed for switching** (video stays for the info screen, D4).

- **2026-10-03 — Phase 2 done:** PicoDVI `DVItext1` (80x30 text at 640x240p60) shows the info screen on HDMI 2; the LG accepts the mode. Video starts first, then `Wire.setClock(50000)`; DDC still ACKs. Flashing without buttons: open the serial port at 1200 baud (core reboots to BOOTSEL), then copy the `.uf2`. Still to check on the desk: Auto Input Switch off, and monitor standby with the Feather's video always on.

- **2026-10-03 — Phase 3 done (fw 0.3.0):** `config.*` (flash via EEPROM emulation, magic + schema + CRC, LG defaults, validation, allowed-pin list incl. BOOT/GPIO7), `ddc.*` (generic 16-bit VCP set), `app.*` (status + actions), `buttons.*` (debounce, keys 1+2 at power-up = factory reset), `protocol.*` (JSON lines via ArduinoJson 7 + bench keys), `screen.*` (reads config). Tested on the board: version/get/set/save/reset, validation errors, `id` echo; saved config survives a reflash.

- **2026-10-03 — Phase 7 done (local):** `web/index.html` + `web/presets.json`. Configure tab (connect by Adafruit USB VID, presets, inputs with Try + auto switch-back to "This computer" after 10 s, keys, client-side validation mirroring the firmware, save/undo, scan, factory reset, restart, live activity log) and Install tab (1200-baud reboot to RPI-RP2, then save `firmware.uf2` onto the drive via the File System Access API, or a local .uf2). Tested on the board in Chrome via `python -m http.server`. Deploying it is Phase 6.

- **2026-10-03 — Phase 5 done:** platform pinned to maxgerhardt/platform-raspberrypi `5d4561a` (→ arduino-pico `fd65f6d`, framework 1.60100.0); libraries pinned (PicoDVI 1.3.2, Adafruit GFX 1.12.6, ArduinoJson 7.4.3); `tools/version.py` stamps `FW_VERSION` (env var from CI → `git describe` → `dev`); DDC sends retry once after 150 ms on NACK. A 0.4.0 build was installed through the web page's Install tab and reported its version correctly.

- **2026-10-03 — Phase 6 written (runs once pushed):** `.github/workflows/firmware.yml` — `build` on every push/PR (version from tag or `git describe`, `.uf2` artifact); on `v*` tags `release` (GitHub Release with `hdmi-ddc-input-switch-<ver>.uf2`) and `pages` (deploys `web/` + that firmware as `firmware.uf2`). Needs Settings → Pages → Source: GitHub Actions.

- **2026-10-03 — Phase 9 done:** the build/use guide lives in the web page's **Guide** tab (parts, print files with download links, wiring, assembly, monitor setup, using it, adding a monitor, troubleshooting); the page opens on the Guide for new visitors and on Configure after a switch has been connected. `README.md` is the repo front page (overview, layout, building firmware/page/case, presets, releases). Renders moved to `web/images/`; CI publishes `web/` + images + `case/export` print files + firmware.

- **2026-10-05 — Phase 8 (case) printed and assembled; keys wired and working.** Second case print (board in the back section, tight port holes with plug recesses and lid tabs). Keys wired with 22 AWG stranded silicone wire: one ground wire window-stripped along the same pin of every switch (pins too short for two wires), one signal wire per key to A0–A3, soldered from the board's underside. Wiring pictures in the Guide (`web/images/wiring-switches.svg`).

## Hardware test checklist

- [x] Boot scan shows `0x37` and `0x50`
- [ ] Switch DP → USB-C → HDMI 1 → HDMI 2 from each button and serial
- [x] Switching works while the monitor displays a *different* input
- [x] Monitor accepts the text-mode video timing
- [ ] With **Auto Input Switch off**, monitor does not jump to HDMI 2 when the PC sleeps/reboots
- [ ] Monitor still enters standby when the active input goes idle (if not: blank video after a timeout)
- [ ] Monitor power cycle → next button press still works
- [ ] Save config → brief video glitch only → config persists across power cycle
- [ ] Factory-reset combo works

## Risks

| Risk | Mitigation |
|---|---|
| Monitor ignores DDC on an inactive input | Always-on video (D4) makes HDMI 2 a live source |
| LG auto-input grabs HDMI 2 | Document: disable Auto Input Switch in OSD |
| Monitor never sleeps with a live source | Test; add video-blank timeout if needed |
| Text-mode timing rejected | Fall back to 640×480 1-bit |
| PicoDVI clock change breaks I²C timing | Re-apply `Wire.setClock` after `display.begin()` |
| Flash write stalls video | Accept; save is rare and user-initiated |
| Web Serial is Chromium-only | Document; manual UF2 fallback |
| STEMMA QT shares the DDC bus | Case should cover/block the port; README warning |

## Future: inline variant (not planned for v1)

Idea: sit **between a source and the monitor** on an input that's already in use, instead of occupying a spare HDMI port.

- **HDMI only, realistically.** HDMI exposes DDC as plain I²C on dedicated pins, so a passthrough board can carry the TMDS pairs straight through and tap SDA/SCL/HPD/+5V. DisplayPort carries DDC over the AUX channel (differential, Manchester-coded) and USB-C carries DP inside alt mode — both need an AUX transceiver at minimum and are much harder. The current setup (DP + USB-C sources) wouldn't benefit.
- **Signal integrity**: TMDS passthrough at HDMI 2.1 rates (up to 48 Gbps FRL) needs a carefully designed PCB with impedance-controlled, length-matched pairs; HDMI 2.0 rates are more forgiving. Off-the-shelf "DDC breakout"/EDID-emulator adapters might serve as a prototype.
- **Shared bus**: the source's GPU is also an I²C master on DDC (EDID reads on hotplug, any DDC/CI software). Inject only when the bus is idle and rely on RP2040 multi-master arbitration-loss detection, or use an I²C bus switch to briefly isolate the source side.
- **Upside**: monitors that only listen to DDC on the *active* input would work.
- **Downside**: no info screen (the source owns the video link).
- **Design hook for now**: keep `ddc.cpp`'s transport behind a small interface (`ddcSend(packet)`) so an inline variant can reuse config, protocol, buttons, and web page unchanged.

## Open items

- Exact allowed-pin list (Phase 0, from schematic)
- Case assembly method and keycap profile (Phase 8)
- Platform commit to pin (Phase 5)
