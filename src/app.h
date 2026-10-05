// What the switch does, shared by the keys, the serial protocol and the screen.
#pragma once
#include <Arduino.h>
#include "config.h"

#ifndef FW_VERSION
#define FW_VERSION "dev"     // normally set by tools/version.py from the git tag
#endif

struct Status {
  bool     ddcSeen = false, edidSeen = false;   // from the last scan
  bool     hasLast = false;                     // anything sent yet?
  char     lastLabel[24] = "";
  uint16_t lastValue = 0;
  bool     lastAck = false;
  uint32_t lastMillis = 0;
};

extern Status status;

bool appSendInput(uint8_t index);                              // config.inputs[index]
bool appSendVcp(uint8_t src, uint8_t vcp, uint16_t value, const char* label);
uint8_t appScan(uint8_t* found, uint8_t max);                  // updates ddcSeen/edidSeen
void appConfigChanged();                                       // re-read keys, redraw
