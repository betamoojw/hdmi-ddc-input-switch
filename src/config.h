// Runtime configuration: what the keys do and how to talk to the monitor.
// Lives in flash (EEPROM emulation) with a schema number and CRC; anything
// missing or invalid falls back to the defaults (LG UltraGear).
#pragma once
#include <Arduino.h>

static const uint16_t CONFIG_SCHEMA = 1;
static const uint8_t  MAX_INPUTS    = 8;
static const uint8_t  MAX_BUTTONS   = 8;
static const uint8_t  NAME_LEN      = 12;   // including the terminator

struct InputDef {
  char     name[NAME_LEN];
  uint16_t value;              // VCP value for this input
};

enum class Action : uint8_t { None = 0, Input = 1, Vcp = 2 };

struct ButtonDef {
  uint8_t  pin;                // GPIO number
  Action   action;
  uint8_t  input;              // Action::Input: index into inputs
  uint8_t  vcp, src;           // Action::Vcp: any VCP "set" (e.g. brightness 0x10)
  uint16_t value;
};

struct Config {
  uint32_t  magic;
  uint16_t  schema;
  char      preset[24];        // display name, e.g. "LG UltraGear"
  uint8_t   vcp;               // input-select VCP code (0x60 MCCS, 0xF4 LG)
  uint8_t   src;               // DDC/CI source address (0x51 MCCS, 0x50 LG)
  uint8_t   numInputs;
  InputDef  inputs[MAX_INPUTS];
  uint8_t   selfInput;         // the input this switch is plugged into (0xFF = unknown)
  uint8_t   numButtons;
  ButtonDef buttons[MAX_BUTTONS];
  uint32_t  crc;
};

extern Config config;

void        configDefaults(Config& c);
bool        configLoad();                       // false: defaults were used
bool        configSave();
// nullptr if valid, otherwise a human-readable reason
const char* configValidate(const Config& c, char* err, size_t errLen);

// Pins a key may use (GPIO numbers), and their Feather labels.
bool        pinAllowed(uint8_t gpio);
const char* pinLabel(uint8_t gpio);
uint8_t     pinFromLabel(const char* label);    // 0xFF if unknown
