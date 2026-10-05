#include "config.h"
#include <EEPROM.h>

Config config;

static const uint32_t MAGIC       = 0x48444443;   // "HDDC"
static const size_t   EEPROM_SIZE = 1024;

// Feather RP2040 DVI header pins a key may use. Excluded: SDA/SCL (GPIO 2/3, the
// monitor's DDC lines), GPIO 4 (NeoPixel), GPIO 16-23 (DVI). BOOT (GPIO 7) is the
// on-board button, isolated by a diode so it reads like any other key.
struct PinName { uint8_t gpio; const char* label; };
static const PinName PINS[] = {
  {26, "A0"}, {27, "A1"}, {28, "A2"}, {29, "A3"}, {24, "D24"}, {25, "D25"},
  {5, "D5"}, {6, "D6"}, {9, "D9"}, {10, "D10"}, {11, "D11"}, {12, "D12"}, {13, "D13"},
  {14, "SCK"}, {15, "MOSI"}, {8, "MISO"}, {0, "TX"}, {1, "RX"}, {7, "BOOT"},
};

bool pinAllowed(uint8_t gpio) {
  for (const auto& p : PINS) if (p.gpio == gpio) return true;
  return false;
}

const char* pinLabel(uint8_t gpio) {
  for (const auto& p : PINS) if (p.gpio == gpio) return p.label;
  return "?";
}

uint8_t pinFromLabel(const char* label) {
  for (const auto& p : PINS) if (strcasecmp(p.label, label) == 0) return p.gpio;
  return 0xFF;
}

static uint32_t crc32(const uint8_t* data, size_t len) {
  uint32_t crc = 0xFFFFFFFF;
  for (size_t i = 0; i < len; i++) {
    crc ^= data[i];
    for (int k = 0; k < 8; k++) crc = (crc >> 1) ^ (0xEDB88320 & -(crc & 1));
  }
  return ~crc;
}

static uint32_t configCrc(const Config& c) {
  return crc32(reinterpret_cast<const uint8_t*>(&c), offsetof(Config, crc));
}

static void setInput(InputDef& in, const char* name, uint16_t value) {
  strncpy(in.name, name, NAME_LEN - 1);
  in.name[NAME_LEN - 1] = 0;
  in.value = value;
}

void configDefaults(Config& c) {
  memset(&c, 0, sizeof c);
  c.magic = MAGIC;
  c.schema = CONFIG_SCHEMA;
  strcpy(c.preset, "LG UltraGear");
  c.vcp = 0xF4;
  c.src = 0x50;
  c.numInputs = 4;
  setInput(c.inputs[0], "HDMI 1", 0x90);
  setInput(c.inputs[1], "HDMI 2", 0x91);
  setInput(c.inputs[2], "DP", 0xD0);
  setInput(c.inputs[3], "USB-C", 0xD1);
  c.selfInput = 1;                            // plugged into HDMI 2
  // Keys left to right as on the printed keycaps, then the on-board BOOT button.
  c.numButtons = 5;
  const uint8_t pins[] = {26, 27, 28, 29};    // A0..A3
  for (uint8_t i = 0; i < 4; i++) c.buttons[i] = {pins[i], Action::Input, i, 0, 0, 0};
  c.buttons[4] = {7, Action::None, 0, 0, 0, 0};
  c.crc = configCrc(c);
}

const char* configValidate(const Config& c, char* err, size_t errLen) {
  if (c.numInputs == 0 || c.numInputs > MAX_INPUTS) {
    snprintf(err, errLen, "inputs: need 1-%u", MAX_INPUTS);
    return err;
  }
  for (uint8_t i = 0; i < c.numInputs; i++) {
    if (!c.inputs[i].name[0]) {
      snprintf(err, errLen, "input %u: name is empty", i + 1);
      return err;
    }
  }
  if (c.selfInput != 0xFF && c.selfInput >= c.numInputs) {
    snprintf(err, errLen, "self: input %u out of range", c.selfInput + 1);
    return err;
  }
  if (c.numButtons > MAX_BUTTONS) {
    snprintf(err, errLen, "buttons: at most %u", MAX_BUTTONS);
    return err;
  }
  for (uint8_t i = 0; i < c.numButtons; i++) {
    const ButtonDef& b = c.buttons[i];
    if (!pinAllowed(b.pin)) {
      snprintf(err, errLen, "button %u: pin %u can't be used", i + 1, b.pin);
      return err;
    }
    for (uint8_t j = 0; j < i; j++) {
      if (c.buttons[j].pin == b.pin) {
        snprintf(err, errLen, "button %u: pin %s already used by button %u", i + 1, pinLabel(b.pin), j + 1);
        return err;
      }
    }
    if (b.action == Action::Input && b.input >= c.numInputs) {
      snprintf(err, errLen, "button %u: input %u doesn't exist", i + 1, b.input + 1);
      return err;
    }
    if (b.action > Action::Vcp) {
      snprintf(err, errLen, "button %u: unknown action", i + 1);
      return err;
    }
  }
  return nullptr;
}

bool configLoad() {
  EEPROM.begin(EEPROM_SIZE);
  Config c;
  EEPROM.get(0, c);
  char err[64];
  if (c.magic != MAGIC || c.schema != CONFIG_SCHEMA || c.crc != configCrc(c) ||
      configValidate(c, err, sizeof err)) {
    configDefaults(config);
    return false;
  }
  config = c;
  return true;
}

bool configSave() {
  config.magic = MAGIC;
  config.schema = CONFIG_SCHEMA;
  config.crc = configCrc(config);
  EEPROM.put(0, config);
  return EEPROM.commit();   // pauses the other core briefly: the video blinks once
}
