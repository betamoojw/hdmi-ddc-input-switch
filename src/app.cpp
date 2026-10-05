#include "app.h"
#include "buttons.h"
#include "ddc.h"
#include "screen.h"

Status status;

static void remember(const char* label, uint16_t value, bool ack) {
  strncpy(status.lastLabel, label, sizeof status.lastLabel - 1);
  status.lastLabel[sizeof status.lastLabel - 1] = 0;
  status.lastValue = value;
  status.lastAck = ack;
  status.lastMillis = millis();
  status.hasLast = true;
  screenTick();
}

bool appSendInput(uint8_t index) {
  if (index >= config.numInputs) return false;
  const InputDef& in = config.inputs[index];
  bool ok = ddcSetVcp(config.src, config.vcp, in.value);
  remember(in.name, in.value, ok);
  return ok;
}

bool appSendVcp(uint8_t src, uint8_t vcp, uint16_t value, const char* label) {
  bool ok = ddcSetVcp(src, vcp, value);
  remember(label, value, ok);
  return ok;
}

uint8_t appScan(uint8_t* found, uint8_t max) {
  uint8_t n = ddcScan(found, max);
  status.ddcSeen = status.edidSeen = false;
  for (uint8_t i = 0; i < n; i++) {
    if (found[i] == DDC_ADDR) status.ddcSeen = true;
    if (found[i] == EDID_ADDR) status.edidSeen = true;
  }
  screenDraw();
  return n;
}

void appConfigChanged() {
  buttonsBegin();
  screenDraw();
}
