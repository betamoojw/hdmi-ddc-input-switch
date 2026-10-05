// hdmi-ddc-input-switch — firmware for an Adafruit Feather RP2040 DVI that switches a
// monitor's input over DDC/CI from mechanical keys, with an info screen on its own
// HDMI output. Behaviour comes from the config in flash (see config.h); the web
// configurator talks to it over USB serial (see protocol.h). PLAN.md has the design.

#include <Arduino.h>
#include <Wire.h>
#include "app.h"
#include "buttons.h"
#include "config.h"
#include "protocol.h"
#include "screen.h"

static const uint32_t SERIAL_WAIT_MS = 1500;   // wait this long for a monitor, never forever

void setup() {
  // Video first: PicoDVI raises the system clock, and everything else must be set
  // up after that (the I2C clock divider in particular).
  bool video = screenBegin();

  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(50000);   // DDC is slow

  bool loaded = configLoad();
  bool factoryReset = buttonsResetHeld();      // hold keys 1 + 2 while plugging in
  if (factoryReset) {
    configDefaults(config);
    configSave();
  }
  buttonsBegin();

  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < SERIAL_WAIT_MS) {}
  uint8_t found[32];
  appScan(found, sizeof found);                // also draws the screen
  protocolBootEvent(loaded, factoryReset, video);
}

void loop() {
  int key = buttonsPoll();
  if (key >= 0) {
    const ButtonDef& b = config.buttons[key];
    bool ok = false;
    if (b.action == Action::Input) ok = appSendInput(b.input);
    else if (b.action == Action::Vcp) ok = appSendVcp(b.src, b.vcp, b.value, "VCP");
    if (b.action != Action::None) protocolKeyEvent(key, ok);
  }

  protocolPoll();

  static uint32_t lastTick = 0;
  if (millis() - lastTick >= 1000) {
    lastTick = millis();
    screenTick();
  }
}
