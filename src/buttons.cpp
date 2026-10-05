#include "buttons.h"
#include "config.h"

static const uint32_t DEBOUNCE_MS   = 30;
static const uint32_t RESET_HOLD_MS = 1000;

static bool     lastState[MAX_BUTTONS];
static uint32_t lastChange[MAX_BUTTONS];

void buttonsBegin() {
  for (uint8_t i = 0; i < config.numButtons; i++) {
    pinMode(config.buttons[i].pin, INPUT_PULLUP);   // each key switches its pin to GND
    lastState[i] = HIGH;
    lastChange[i] = millis();
  }
}

int buttonsPoll() {
  uint32_t now = millis();
  for (uint8_t i = 0; i < config.numButtons; i++) {
    bool s = digitalRead(config.buttons[i].pin);
    // first edge after a quiet period wins; bounces within DEBOUNCE_MS are ignored
    if (s != lastState[i] && now - lastChange[i] > DEBOUNCE_MS) {
      lastChange[i] = now;
      lastState[i] = s;
      if (s == LOW) return i;
    }
  }
  return -1;
}

bool buttonsResetHeld() {
  if (config.numButtons < 2) return false;
  uint8_t a = config.buttons[0].pin, b = config.buttons[1].pin;
  pinMode(a, INPUT_PULLUP);
  pinMode(b, INPUT_PULLUP);
  delay(5);
  uint32_t t0 = millis();
  while (millis() - t0 < RESET_HOLD_MS) {
    if (digitalRead(a) == HIGH || digitalRead(b) == HIGH) return false;
    delay(10);
  }
  return true;
}
