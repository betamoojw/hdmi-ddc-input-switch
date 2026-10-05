#include "ddc.h"
#include <Wire.h>

static const uint32_t DDC_GAP_MS = 50;   // monitors need a pause between commands

static const uint32_t RETRY_GAP_MS = 150;   // a monitor waking from standby can miss the first one

static bool sendOnce(const uint8_t* pkt, size_t len, uint8_t cs) {
  Wire.beginTransmission(DDC_ADDR);
  Wire.write(pkt, len);
  Wire.write(cs);
  uint8_t err = Wire.endTransmission();
  delay(DDC_GAP_MS);
  return err == 0;
}

bool ddcSetVcp(uint8_t src, uint8_t vcp, uint16_t value) {
  uint8_t pkt[] = {src, 0x84, 0x03, vcp, (uint8_t)(value >> 8), (uint8_t)(value & 0xFF)};
  uint8_t cs = 0x6E;
  for (uint8_t b : pkt) cs ^= b;
  if (sendOnce(pkt, sizeof pkt, cs)) return true;
  delay(RETRY_GAP_MS);
  return sendOnce(pkt, sizeof pkt, cs);   // one retry
}

uint8_t ddcScan(uint8_t* found, uint8_t max) {
  uint8_t n = 0;
  for (uint8_t a = 1; a < 127 && n < max; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) found[n++] = a;
  }
  return n;
}
