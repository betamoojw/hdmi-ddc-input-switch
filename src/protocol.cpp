#include "protocol.h"
#include <ArduinoJson.h>
#include "app.h"
#include "config.h"

static const size_t LINE_MAX = 1536;
static char  line[LINE_MAX];
static size_t lineLen = 0;
static bool  inJson = false;

static const char* actionName(Action a) {
  switch (a) {
    case Action::Input: return "input";
    case Action::Vcp:   return "vcp";
    default:            return "none";
  }
}

static void reply(JsonDocument& doc) {
  serializeJson(doc, Serial);
  Serial.println();
}

static void replyError(const char* msg, JsonVariantConst id) {
  JsonDocument doc;
  if (!id.isNull()) doc["id"] = id;
  doc["ok"] = false;
  doc["error"] = msg;
  reply(doc);
}

static void configToJson(const Config& c, JsonObject out) {
  out["preset"] = c.preset;
  out["vcp"] = c.vcp;
  out["src"] = c.src;
  out["self"] = c.selfInput == 0xFF ? -1 : (int)c.selfInput;   // -1 = not one of the inputs
  JsonArray inputs = out["inputs"].to<JsonArray>();
  for (uint8_t i = 0; i < c.numInputs; i++) {
    JsonObject in = inputs.add<JsonObject>();
    in["name"] = c.inputs[i].name;
    in["value"] = c.inputs[i].value;
  }
  JsonArray buttons = out["buttons"].to<JsonArray>();
  for (uint8_t i = 0; i < c.numButtons; i++) {
    const ButtonDef& b = c.buttons[i];
    JsonObject o = buttons.add<JsonObject>();
    o["pin"] = pinLabel(b.pin);
    o["action"] = actionName(b.action);
    if (b.action == Action::Input) o["input"] = b.input;
    if (b.action == Action::Vcp) {
      o["vcp"] = b.vcp;
      o["src"] = b.src;
      o["value"] = b.value;
    }
  }
}

// Parse a config object into `c` (starting from the current config, so partial
// updates work). Returns nullptr on success or an error message.
static const char* configFromJson(JsonObjectConst in, Config& c, char* err, size_t errLen) {
  if (in["preset"].is<const char*>()) {
    strncpy(c.preset, in["preset"].as<const char*>(), sizeof c.preset - 1);
    c.preset[sizeof c.preset - 1] = 0;
  }
  if (!in["vcp"].isNull()) c.vcp = in["vcp"].as<uint8_t>();
  if (!in["src"].isNull()) c.src = in["src"].as<uint8_t>();
  if (in["self"].is<int>()) {
    int v = in["self"];
    c.selfInput = v < 0 ? 0xFF : (uint8_t)v;
  }

  if (in["inputs"].is<JsonArrayConst>()) {
    JsonArrayConst arr = in["inputs"];
    if (arr.size() > MAX_INPUTS) { snprintf(err, errLen, "inputs: at most %u", MAX_INPUTS); return err; }
    c.numInputs = arr.size();
    for (uint8_t i = 0; i < c.numInputs; i++) {
      const char* name = arr[i]["name"] | "";
      if (strlen(name) >= NAME_LEN) {
        snprintf(err, errLen, "input %u: name longer than %u characters", i + 1, NAME_LEN - 1);
        return err;
      }
      strcpy(c.inputs[i].name, name);
      c.inputs[i].value = arr[i]["value"] | 0;
    }
  }

  if (in["buttons"].is<JsonArrayConst>()) {
    JsonArrayConst arr = in["buttons"];
    if (arr.size() > MAX_BUTTONS) { snprintf(err, errLen, "buttons: at most %u", MAX_BUTTONS); return err; }
    c.numButtons = arr.size();
    for (uint8_t i = 0; i < c.numButtons; i++) {
      JsonObjectConst o = arr[i];
      ButtonDef& b = c.buttons[i];
      memset(&b, 0, sizeof b);
      if (o["pin"].is<const char*>()) {
        b.pin = pinFromLabel(o["pin"]);
        if (b.pin == 0xFF) {
          snprintf(err, errLen, "button %u: pin '%s' can't be used", i + 1, o["pin"].as<const char*>());
          return err;
        }
      } else {
        b.pin = o["pin"] | 0xFF;
      }
      const char* act = o["action"] | "none";
      if (!strcmp(act, "input")) b.action = Action::Input;
      else if (!strcmp(act, "vcp")) b.action = Action::Vcp;
      else if (!strcmp(act, "none")) b.action = Action::None;
      else { snprintf(err, errLen, "button %u: unknown action '%s'", i + 1, act); return err; }
      b.input = o["input"] | 0;
      b.vcp = o["vcp"] | 0;
      b.src = o["src"] | c.src;
      b.value = o["value"] | 0;
    }
  }
  return configValidate(c, err, errLen);
}

static void handleJson(const char* text) {
  JsonDocument req;
  if (deserializeJson(req, text)) { replyError("bad JSON", JsonVariantConst()); return; }
  JsonVariantConst id = req["id"];
  const char* cmd = req["cmd"] | "";
  JsonDocument doc;
  if (!id.isNull()) doc["id"] = id;
  char err[80];

  if (!strcmp(cmd, "version")) {
    doc["ok"] = true;
    doc["fw"] = FW_VERSION;
    doc["schema"] = CONFIG_SCHEMA;
    doc["board"] = "adafruit_feather_rp2040_dvi";
    doc["maxInputs"] = MAX_INPUTS;
    doc["maxButtons"] = MAX_BUTTONS;
    doc["nameLen"] = NAME_LEN - 1;
    JsonArray pins = doc["pins"].to<JsonArray>();
    for (uint8_t g = 0; g < 30; g++) if (pinAllowed(g)) pins.add(pinLabel(g));
  } else if (!strcmp(cmd, "get")) {
    doc["ok"] = true;
    configToJson(config, doc["config"].to<JsonObject>());
  } else if (!strcmp(cmd, "set")) {
    if (!req["config"].is<JsonObjectConst>()) { replyError("set: missing config", id); return; }
    Config c = config;
    if (configFromJson(req["config"], c, err, sizeof err)) { replyError(err, id); return; }
    config = c;
    appConfigChanged();
    doc["ok"] = true;
    doc["saved"] = false;
  } else if (!strcmp(cmd, "save")) {
    doc["ok"] = configSave();
    if (!doc["ok"]) doc["error"] = "flash write failed";
  } else if (!strcmp(cmd, "send")) {
    int index = -1;
    if (req["input"].is<int>()) index = req["input"];
    else if (req["name"].is<const char*>()) {
      for (uint8_t i = 0; i < config.numInputs; i++)
        if (!strcasecmp(config.inputs[i].name, req["name"])) index = i;
    }
    if (index < 0 || index >= config.numInputs) { replyError("send: no such input", id); return; }
    doc["ok"] = true;
    doc["ack"] = appSendInput(index);
  } else if (!strcmp(cmd, "raw")) {
    if (req["vcp"].isNull() || req["value"].isNull()) { replyError("raw: need vcp and value", id); return; }
    uint8_t src = req["src"] | config.src;
    doc["ok"] = true;
    doc["ack"] = appSendVcp(src, req["vcp"], req["value"], "raw");
  } else if (!strcmp(cmd, "scan")) {
    uint8_t found[32];
    uint8_t n = appScan(found, sizeof found);
    doc["ok"] = true;
    JsonArray a = doc["devices"].to<JsonArray>();
    for (uint8_t i = 0; i < n; i++) a.add(found[i]);
    doc["ddc"] = status.ddcSeen;
    doc["edid"] = status.edidSeen;
  } else if (!strcmp(cmd, "reset")) {
    configDefaults(config);
    bool saved = configSave();
    appConfigChanged();
    doc["ok"] = saved;
    doc["saved"] = saved;
  } else if (!strcmp(cmd, "reboot")) {
    doc["ok"] = true;
    reply(doc);
    Serial.flush();
    delay(100);
    rp2040.reboot();
  } else if (!strcmp(cmd, "bootloader")) {
    doc["ok"] = true;
    reply(doc);
    Serial.flush();
    delay(100);
    rp2040.rebootToBootloader();
  } else {
    snprintf(err, sizeof err, "unknown cmd '%s'", cmd);
    replyError(err, id);
    return;
  }
  reply(doc);
}

static void handleKey(char c) {
  if (c >= '1' && c <= '8') {
    uint8_t i = c - '1';
    if (i >= config.numInputs) { Serial.printf("No input %c (have %u)\n", c, config.numInputs); return; }
    bool ok = appSendInput(i);
    Serial.printf("-> %s (0x%02X): %s\n", config.inputs[i].name, config.inputs[i].value, ok ? "ACK" : "NO ACK");
  } else if (c == 's') {
    uint8_t found[32];
    uint8_t n = appScan(found, sizeof found);
    Serial.print("I2C devices:");
    for (uint8_t i = 0; i < n; i++) Serial.printf(" 0x%02X", found[i]);
    Serial.println("   (expect 0x37 DDC/CI and 0x50 EDID)");
  } else if (c == '?' || c == 'h') {
    Serial.printf("hdmi-ddc-input-switch v%s  (%s)\n", FW_VERSION, config.preset);
    for (uint8_t i = 0; i < config.numInputs; i++)
      Serial.printf("  %u = %s (0x%02X)\n", i + 1, config.inputs[i].name, config.inputs[i].value);
    Serial.println("  s = I2C scan, ? = this help");
    Serial.println("  JSON: {\"cmd\":\"version|get|set|save|send|raw|scan|reset|reboot|bootloader\"}");
  }
}

void protocolPoll() {
  while (Serial.available()) {
    char c = Serial.read();
    if (inJson) {
      if (c == '\n' || c == '\r') {
        line[lineLen] = 0;
        inJson = false;
        handleJson(line);
        lineLen = 0;
      } else if (lineLen < LINE_MAX - 1) {
        line[lineLen++] = c;
      } else {
        inJson = false;
        lineLen = 0;
        replyError("line too long", JsonVariantConst());
      }
    } else if (c == '{') {
      inJson = true;
      line[0] = c;
      lineLen = 1;
    } else if (c != '\n' && c != '\r' && c != ' ') {
      handleKey(c);
    }
  }
}

void protocolEvent(const char* json) { Serial.println(json); }

void protocolKeyEvent(uint8_t key, bool ok) {
  JsonDocument doc;
  doc["event"] = "key";
  doc["key"] = key;
  doc["label"] = status.lastLabel;
  doc["value"] = status.lastValue;
  doc["ack"] = ok;
  reply(doc);
}

void protocolBootEvent(bool configLoaded, bool factoryReset, bool video) {
  JsonDocument doc;
  doc["event"] = "boot";
  doc["fw"] = FW_VERSION;
  doc["config"] = factoryReset ? "factory reset" : (configLoaded ? "loaded" : "defaults");
  doc["video"] = video;
  doc["ddc"] = status.ddcSeen;
  doc["edid"] = status.edidSeen;
  reply(doc);
}
