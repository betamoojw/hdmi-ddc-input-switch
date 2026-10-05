# hdmi-ddc-input-switch — Project Brief

## Goal

Firmware for a small desk box with physical mechanical-key buttons that switches a monitor's input. The box is an **Adafruit Feather RP2040 DVI** connected to one of the monitor's HDMI ports; it sends DDC/CI commands over that port's I²C (DDC) lines.

The project should be **generic**, so it works with any DDC/CI monitor through per-monitor profiles. The first target, and the only one tested so far, is the **LG 45GR75DC-B UltraGear**, which uses a nonstandard LG method (see Protocol).

Keep it simple and appliance-like: instant-on, no network, no status LEDs.

## Hardware

- **Board:** Adafruit Feather RP2040 DVI (product 5710). The HDMI connector's DDC SDA/SCL are wired to the Feather's main SDA/SCL through an onboard level shifter, so `Wire` talks to the monitor directly.
- **Connection:** Feather HDMI → monitor **HDMI 2** (dedicated control port). Monitor inputs in use: DisplayPort and USB-C. HDMI 1 is free for future use.
- **Buttons:** Kailh Brown (MX-compatible) switches, each wired between a GPIO pin and GND. Use internal pull-ups, no external resistors.
- **Power:** USB-C.
- **Do not** attach anything to the STEMMA QT port. It shares the I²C bus with the monitor's DDC line.

## Protocol

### Standard DDC/CI input switching (most monitors)

- VCP code **0x60** (Input Source), source address **0x51**
- Packet bytes: `0x51, 0x84, 0x03, 0x60, 0x00, <value>, <checksum>`
- Common MCCS values: `0x0F` DP1, `0x10` DP2, `0x11` HDMI1, `0x12` HDMI2. Vendors vary, so values belong in the profile.

### Input switching (LG proprietary)

LG ignores the standard VCP 0x60 input select. It uses proprietary **VCP 0xF4** sent with **source address 0x50** (not the standard 0x51). This has been confirmed working on this monitor using deskmux on Windows.

- I²C 7-bit address: `0x37` (DDC/CI, 0x6E write address)
- Packet bytes: `0x50, 0x84, 0x03, 0xF4, 0x00, <value>, <checksum>`
- Checksum: XOR of `0x6E` and every preceding packet byte
- Wait ~50 ms between DDC commands
- The monitor does **not** report the current input via this sidechannel. Don't attempt read-back.

| Input       | Value  |
|-------------|--------|
| DisplayPort | `0xD0` |
| USB-C       | `0xD1` |
| HDMI 1      | `0x90` |
| HDMI 2      | `0x91` (the Feather's own port) |

## Requirements

0. **Monitor profiles:** a profile struct holds the VCP code, source address, and a named table of input values. Ship two profiles, `LG_ULTRAGEAR` (0xF4 / 0x50) and `MCCS_STANDARD` (0x60 / 0x51), selected at compile time (e.g. a build flag in `platformio.ini`). Adding a monitor should mean adding a profile, never changing the core logic. Document how to add one in the README.
1. **Button handling:** a configurable array maps each button pin to an input value. Default mapping:
   - `A0` → DisplayPort
   - `A1` → USB-C
   - `A2` → HDMI 1
   - The button count must be easy to change (2–4 buttons) by editing one array.
2. **Fire on press**, with ~30 ms debounce. No repeat while held.
3. **Serial test interface** at 115200 baud for bench testing without buttons:
   - `d` = DP, `c` = USB-C, `1` = HDMI 1, `2` = HDMI 2, `s` = I²C bus scan
   - Log each send with ACK/NACK from `Wire.endTransmission()`
4. **Boot diagnostic:** I²C scan on startup. A connected monitor should show `0x37` (DDC/CI) and `0x50` (EDID).
5. I²C clock 50 kHz (DDC is slow).

## Build setup (PlatformIO)

```ini
[env:feather_dvi]
platform = https://github.com/maxgerhardt/platform-raspberrypi.git
board = adafruit_feather_dvi
framework = arduino
board_build.core = earlephilhower
monitor_speed = 115200
```

- Use the maxgerhardt platform fork (the official `raspberrypi` platform only ships Arduino-Mbed). Pin it to a specific commit once the build works.
- If `adafruit_feather_dvi` doesn't resolve, check `pio boards rp2040`.
- Source in `src/main.cpp` with `#include <Arduino.h>`.
- First upload: hold BOOT, tap RESET. Later uploads auto-reset.

## Known unknown — video fallback (conditional)

It's unconfirmed whether the monitor accepts DDC commands on an HDMI input that isn't currently displayed. Bench test: Feather on HDMI 2, monitor showing DP, send `1`, and check whether it switches to HDMI 1.

**If it doesn't work**, add a fallback: have the Feather output a solid black DVI signal (Adafruit's PicoDVI fork, 320x240 framebuffer) so the monitor sees a live source on HDMI 2. Notes:
- DVI generation uses one full core, both PIOs, and ~150K SRAM. Keep button/DDC logic on the other core or in the main loop accordingly.
- I²C is hardware, separate from the PIOs, so DDC should still work alongside video.
- Make the fallback a compile-time flag (e.g. `#define ENABLE_DVI_KEEPALIVE`) so both modes can be tested.

Don't implement this unless the bench test shows it's needed, or implement it behind the flag, defaulted off.

## Out of scope

- Wi-Fi/network control
- Status LEDs / NeoPixel
- Brightness, contrast, volume controls
- A status-page display

## Reference implementation (starting point — LG-specific, refactor into profiles)

```cpp
#include <Arduino.h>
#include <Wire.h>

const uint8_t BTN_PINS[]   = {A0, A1, A2};
const uint8_t INPUT_CODE[] = {0xD0, 0xD1, 0x90};   // DP, USB-C, HDMI1
const char*   INPUT_NAME[] = {"DP", "USB-C", "HDMI1"};
const int     NUM_BTNS     = sizeof(BTN_PINS) / sizeof(BTN_PINS[0]);

const uint8_t  DDC_ADDR    = 0x37;
const uint32_t DEBOUNCE_MS = 30;

bool     lastState[NUM_BTNS];
uint32_t lastChange[NUM_BTNS];

bool lgInput(uint8_t value) {
  uint8_t pkt[] = {0x50, 0x84, 0x03, 0xF4, 0x00, value};
  uint8_t cs = 0x6E;
  for (uint8_t b : pkt) cs ^= b;
  Wire.beginTransmission(DDC_ADDR);
  Wire.write(pkt, sizeof pkt);
  Wire.write(cs);
  uint8_t err = Wire.endTransmission();
  delay(50);
  return err == 0;
}

void sendCode(uint8_t code, const char* name) {
  bool ok = lgInput(code);
  Serial.printf("-> %s (0x%02X): %s\n", name, code, ok ? "ACK" : "NO ACK");
}

void scanBus() {
  Serial.print("I2C devices:");
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) Serial.printf(" 0x%02X", a);
  }
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(50000);
  for (int i = 0; i < NUM_BTNS; i++) {
    pinMode(BTN_PINS[i], INPUT_PULLUP);
    lastState[i] = HIGH;
    lastChange[i] = 0;
  }
  delay(1500);
  Serial.println("Ready. d=DP c=USB-C 1=HDMI1 2=HDMI2 s=scan");
  scanBus();
}

void loop() {
  for (int i = 0; i < NUM_BTNS; i++) {
    bool s = digitalRead(BTN_PINS[i]);
    if (s != lastState[i] && millis() - lastChange[i] > DEBOUNCE_MS) {
      lastChange[i] = millis();
      lastState[i] = s;
      if (s == LOW) sendCode(INPUT_CODE[i], INPUT_NAME[i]);
    }
  }
  if (Serial.available()) {
    switch (Serial.read()) {
      case 'd': sendCode(0xD0, "DP");    break;
      case 'c': sendCode(0xD1, "USB-C"); break;
      case '1': sendCode(0x90, "HDMI1"); break;
      case '2': sendCode(0x91, "HDMI2"); break;
      case 's': scanBus();               break;
    }
  }
}
```

## Acceptance criteria

- Builds and uploads via PlatformIO.
- Boot scan shows `0x37` and `0x50` with the monitor connected.
- Serial commands and buttons switch the monitor to the mapped input.
- Changing the button mapping requires editing only the arrays at the top.
