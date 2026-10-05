#include "screen.h"
#include "app.h"
#include "config.h"

// Project page (configurator + firmware installer); forks can override with -D PROJECT_URL=...
#ifndef PROJECT_URL
#define PROJECT_URL "https://jeyeager65.github.io/hdmi-ddc-input-switch/"
#endif

#ifndef DISABLE_VIDEO
#include <PicoDVI.h>

// 640x240 with 8x8 cells = 80 columns x 30 rows ("tall" pixels, VGA-text style).
static DVItext1 tv(DVI_RES_640x240p60, adafruit_feather_dvi_cfg);
static const int COLS = 80;
static const int ROW_LAST = 21, ROW_UP = 28;

// Write text at a cell; inverse video sets the cell's high byte.
static void put(int col, int row, const char* text, bool inverse = false) {
  for (int i = 0; text[i] && col + i < COLS; i++) {
    tv.drawPixel(col + i, row, (uint8_t)text[i] | (inverse ? 0xFF00 : 0));
  }
}

static void clearRow(int row, bool inverse = false) {
  for (int c = 0; c < COLS; c++) tv.drawPixel(c, row, ' ' | (inverse ? 0xFF00 : 0));
}

static void putf(int col, int row, const char* fmt, ...) {
  char buf[COLS + 1];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof buf, fmt, ap);
  va_end(ap);
  put(col, row, buf);
}

bool screenBegin() { return tv.begin(); }

static void describe(const ButtonDef& b, char* out, size_t len) {
  switch (b.action) {
    case Action::Input:
      snprintf(out, len, "%-11s (0x%02X)", config.inputs[b.input].name, config.inputs[b.input].value);
      break;
    case Action::Vcp:
      snprintf(out, len, "VCP 0x%02X = %u (src 0x%02X)", b.vcp, b.value, b.src);
      break;
    default:
      snprintf(out, len, "-");
  }
}

static void drawLast() {
  clearRow(ROW_LAST);
  if (!status.hasLast) {
    put(2, ROW_LAST, "Last command:  none yet");
    return;
  }
  uint32_t ago = (millis() - status.lastMillis) / 1000;
  putf(2, ROW_LAST, "Last command:  %s (0x%02X)  %s   %lu s ago", status.lastLabel, status.lastValue,
       status.lastAck ? "ACK" : "NO ACK", (unsigned long)ago);
}

static void drawUptime() {
  uint32_t t = millis() / 1000;
  clearRow(ROW_UP);
  putf(2, ROW_UP, "Up %lu:%02lu:%02lu", (unsigned long)(t / 3600), (unsigned long)(t / 60 % 60),
       (unsigned long)(t % 60));
}

void screenDraw() {
  tv.fillScreen(' ');
  clearRow(0, true);
  put(2, 0, "HDMI-DDC INPUT SWITCH", true);
  put(COLS - 12, 0, "v" FW_VERSION, true);

  if (config.selfInput < config.numInputs) {
    putf(2, 2, "You are looking at %s - the switch's own port.", config.inputs[config.selfInput].name);
  } else {
    put(2, 2, "You are looking at the switch's own port.");
  }
  put(2, 3, "Press a key to switch the monitor to another input.");

  putf(2, 5, "Monitor:  %s   (input select: VCP 0x%02X, source 0x%02X)", config.preset, config.vcp, config.src);

  put(2, 7, "Keys");
  put(2, 8, "----");
  for (uint8_t i = 0; i < config.numButtons && i < MAX_BUTTONS; i++) {
    char what[40];
    describe(config.buttons[i], what, sizeof what);
    putf(4, 9 + i, "[%u] %-5s %s", i + 1, pinLabel(config.buttons[i].pin), what);
  }

  putf(2, 19, "DDC/CI 0x37: %s     EDID 0x50: %s", status.ddcSeen ? "OK" : "--", status.edidSeen ? "OK" : "--");
  drawLast();

  put(2, 23, "Set up / update:  " PROJECT_URL);
  put(2, 24, "Serial 115200:  1-8 = send input   s = I2C scan   ? = help");
  put(2, 25, "                {\"cmd\":\"...\"} = JSON commands for the web configurator");
  drawUptime();
}

void screenTick() {
  drawLast();
  drawUptime();
}

#else

bool screenBegin() { return true; }
void screenDraw() {}
void screenTick() {}

#endif
