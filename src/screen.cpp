#include "screen.h"
#include "app.h"
#include "config.h"

// Project page (configurator + firmware installer); forks can override with -D PROJECT_URL=...
#ifndef PROJECT_URL
#define PROJECT_URL "https://jeyeager65.github.io/hdmi-ddc-input-switch/"
#endif

#ifndef DISABLE_VIDEO
#include <PicoDVI.h>
// Fonts: Noto Sans at exact pixel sizes, made by tools/gfxfont.py (see src/fonts/).
#include "fonts/Sans15.h"
#include "fonts/Sans17.h"
#include "fonts/SansBold14.h"
#include "fonts/SansBold15.h"
#include "fonts/SansBold28.h"

// 640x480, 1 bit per pixel (38 KB), drawn with Adafruit GFX.
// 640x480p60 uses the same 25.2 MHz pixel clock as PicoDVI's 640x240 text mode.
static DVIGFX1 tv(DVI_RES_640x480p60, false, adafruit_feather_dvi_cfg);
static const uint16_t FG = 1, BG = 0;
static const int W = 640, M = 24;              // screen width, outer margin

// Layout (y values are tops unless named *_BASE, which are text baselines)
static const int PANEL_Y = 132, PANEL_B = 404;  // panels: top and bottom
static const int KEYS_X = M, KEYS_W = 368;
static const int SIDE_X = KEYS_X + KEYS_W + 16, SIDE_W = W - M - SIDE_X;
static const int MON_Y = PANEL_Y, MON_B = 262;
static const int TIPS_Y = 280, TIPS_B = PANEL_B;
static const int FOOT_Y = 420;

// ---- drawing helpers -------------------------------------------------------------
// Width from the glyphs' advances, not their ink, so right-aligned text whose digits
// change (the uptime) keeps its left edge still; the fonts have tabular digits.
static int textWidth(const char* s, const GFXfont* f) {
  int w = 0;
  for (; *s; s++) {
    uint8_t c = *s;
    if (c >= f->first && c <= f->last) w += f->glyph[c - f->first].xAdvance;
  }
  return w;
}

static void text(int x, int base, const char* s, const GFXfont* f, uint16_t c = FG) {
  tv.setFont(f);
  tv.setTextColor(c);
  tv.setCursor(x, base);
  tv.print(s);
}

static void textRight(int right, int base, const char* s, const GFXfont* f, uint16_t c = FG) {
  text(right - textWidth(s, f), base, s, f, c);
}

static void textf(int x, int base, const GFXfont* f, const char* fmt, ...) {
  char buf[96];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof buf, fmt, ap);
  va_end(ap);
  text(x, base, buf, f);
}

// Rounded 2 px frame with its title set into the top edge, like a fieldset.
static void panel(int x, int y, int w, int h, const char* title) {
  tv.drawRoundRect(x, y, w, h, 10, FG);
  tv.drawRoundRect(x + 1, y + 1, w - 2, h - 2, 9, FG);
  int tw = textWidth(title, &SansBold14);
  tv.fillRect(x + 14, y - 2, tw + 12, 6, BG);
  text(x + 20, y + 5, title, &SansBold14);
}

// ---- video on/off ----------------------------------------------------------------
// Output on/off: PicoDVI keeps running, but the output drivers of its pins (4
// differential pairs: clock and 3 TMDS lanes) are switched off with the output-enable
// override, so the port carries no signal. Only that override is touched: the pins
// keep their function and PicoDVI's invert override (the Feather's pairs are swapped;
// losing it inverts every pixel).
static const uint32_t SCREEN_TIMEOUT_MS = 5UL * 60 * 1000;
static uint8_t dviPins[8];
static bool videoOn = false, videoOk = false;
static uint32_t videoSince = 0;

bool screenBegin() {
  videoOk = tv.begin();
  if (!videoOk) return false;
  tv.setTextWrap(false);
  const dvi_serialiser_cfg& c = adafruit_feather_dvi_cfg;
  uint8_t bases[4] = {(uint8_t)c.pins_clk, (uint8_t)c.pins_tmds[0], (uint8_t)c.pins_tmds[1],
                      (uint8_t)c.pins_tmds[2]};
  for (int i = 0; i < 4; i++) {
    dviPins[2 * i] = bases[i];
    dviPins[2 * i + 1] = bases[i] + 1;
  }
  videoOn = true;
  screenVideo(false);
  return true;
}

void screenVideo(bool on) {
  if (!videoOk) return;
  if (on) videoSince = millis();
  if (on == videoOn) return;
  for (int i = 0; i < 8; i++) {
    // off: drivers disabled (high impedance), no clock, no signal
    gpio_set_oeover(dviPins[i], on ? GPIO_OVERRIDE_NORMAL : GPIO_OVERRIDE_LOW);
  }
  videoOn = on;
}

bool screenVideoOn() { return videoOn; }

// ---- content ---------------------------------------------------------------------
static void drawKeys() {
  panel(KEYS_X, PANEL_Y, KEYS_W, PANEL_B - PANEL_Y, "KEYS");
  int n = config.numButtons < MAX_BUTTONS ? config.numButtons : MAX_BUTTONS;
  int rowH = n > 6 ? 30 : 38;
  int y = PANEL_Y + 22;
  for (int i = 0; i < n; i++, y += rowH) {
    const ButtonDef& b = config.buttons[i];
    bool self = b.action == Action::Input && b.input == config.selfInput;
    uint16_t fg = self ? BG : FG;
    // the input you're looking at: a filled bar behind the row
    if (self) tv.fillRoundRect(KEYS_X + 10, y - 5, KEYS_W - 20, 36, 8, FG);
    // a little keycap: the key number, or B for the board's BOOT button
    bool boot = !strcmp(pinLabel(b.pin), "BOOT");
    char cap[4];
    snprintf(cap, sizeof cap, boot ? "B" : "%d", i + 1);
    tv.drawRoundRect(KEYS_X + 18, y, 26, 26, 6, fg);
    text(KEYS_X + 31 - textWidth(cap, &SansBold15) / 2, y + 19, cap, &SansBold15, fg);

    char what[32], detail[32];
    if (b.action == Action::Input && b.input < config.numInputs) {
      snprintf(what, sizeof what, "%s", config.inputs[b.input].name);
      snprintf(detail, sizeof detail, "%s", self ? "this screen" : pinLabel(b.pin));
    } else if (b.action == Action::Vcp) {
      snprintf(what, sizeof what, "VCP 0x%02X = %u", b.vcp, b.value);
      snprintf(detail, sizeof detail, "%s", pinLabel(b.pin));
    } else {
      snprintf(what, sizeof what, "Not used");
      detail[0] = 0;
    }
    text(KEYS_X + 56, y + 20, what, &Sans17, fg);
    if (detail[0]) textRight(KEYS_X + KEYS_W - 22, y + 18, detail, &Sans15, fg);
  }
}

static void drawMonitor() {
  panel(SIDE_X, MON_Y, SIDE_W, MON_B - MON_Y, "MONITOR");
  int x = SIDE_X + 16, y = MON_Y + 38;
  text(x, y, config.preset, &Sans17);
  textf(x, y + 26, &Sans15, "Input select: VCP 0x%02X", config.vcp);
  textf(x, y + 46, &Sans15, "from source 0x%02X", config.src);
  textf(x, y + 72, &Sans15, "DDC/CI %s    EDID %s", status.ddcSeen ? "OK" : "--", status.edidSeen ? "OK" : "--");
}

// Static help for a box with no manual. (A "last command" panel would always show the
// switch's own input: pressing that key is how you get to this screen.)
static void drawTips() {
  panel(SIDE_X, TIPS_Y, SIDE_W, TIPS_B - TIPS_Y, "TIPS");
  int x = SIDE_X + 16, y = TIPS_Y + 32;
  text(x, y, "R restarts the switch.", &Sans15);
  text(x, y + 26, "Factory reset: hold 1+2", &Sans15);
  text(x, y + 46, "while plugging in.", &Sans15);
  text(x, y + 72, "Change keys: see below.", &Sans15);
}

static void drawUptime() {
  uint32_t t = millis() / 1000;
  char buf[24];
  snprintf(buf, sizeof buf, "Up %lu:%02lu:%02lu", (unsigned long)(t / 3600), (unsigned long)(t / 60 % 60),
           (unsigned long)(t % 60));
  tv.fillRect(W - M - 110, FOOT_Y + 14, 110, 24, BG);
  textRight(W - M, FOOT_Y + 32, buf, &Sans15);
}

void screenDraw() {
  tv.fillScreen(BG);

  // title, and the version in a pill
  text(M, 42, "HDMI-DDC Input Switch", &SansBold28);
  {
    const char* v = "v" FW_VERSION;
    int vw = textWidth(v, &Sans15) + 24;
    tv.drawRoundRect(W - M - vw, 18, vw, 28, 14, FG);
    text(W - M - vw + 12, 37, v, &Sans15);
  }

  // where you are
  if (config.selfInput < config.numInputs) {
    textf(M, 88, &Sans17, "You're looking at %s, the switch's own port.", config.inputs[config.selfInput].name);
  } else {
    text(M, 88, "You're looking at the switch's own port.", &Sans17);
  }
  text(M, 112, "Press a key to switch the monitor to another input.", &Sans15);

  drawKeys();
  drawMonitor();
  drawTips();

  // footer
  tv.drawFastHLine(M, FOOT_Y, W - 2 * M, FG);
  text(M, FOOT_Y + 32, "Set up:  " PROJECT_URL, &Sans15);
  drawUptime();
}

void screenTick() {
  drawUptime();
  if (videoOn && millis() - videoSince >= SCREEN_TIMEOUT_MS) screenVideo(false);
}

bool screenSize(int& w, int& h) {
  w = videoOk ? tv.width() : 0;
  h = videoOk ? tv.height() : 0;
  return videoOk;
}

void screenDump(Print& out) {
  static const char hex[] = "0123456789abcdef";
  const uint8_t* fb = tv.getBuffer();
  int stride = (tv.width() + 7) / 8;
  char line[2 * 80 + 2];
  for (int y = 0; y < tv.height(); y++) {
    const uint8_t* row = fb + y * stride;
    line[0] = '#';
    for (int i = 0; i < stride && i < 80; i++) {
      line[1 + 2 * i] = hex[row[i] >> 4];
      line[2 + 2 * i] = hex[row[i] & 15];
    }
    line[1 + 2 * stride] = 0;
    out.println(line);
    out.flush();
    delay(2);                     // USB serial drops data if we outrun the host
  }
}

#else

bool screenSize(int& w, int& h) { w = h = 0; return false; }
void screenDump(Print&) {}

bool screenBegin() { return true; }
void screenDraw() {}
void screenTick() {}
void screenVideo(bool) {}
bool screenVideoOn() { return false; }

#endif
