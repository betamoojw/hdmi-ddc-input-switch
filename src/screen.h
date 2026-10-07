// Info screen on the Feather's own HDMI output (640x480 1-bit graphics, PicoDVI +
// Adafruit GFX fonts). The monitor shows it when switched to the input the switch is
// plugged into. Content comes from `config` and `status`. Build with -D DISABLE_VIDEO to
// leave the port without a picture.
#pragma once
#include <Arduino.h>

bool screenBegin();    // false if video failed to start; starts with the output off
void screenDraw();     // full redraw
void screenTick();     // once a second: uptime, and the video timeout

// The HDMI output only carries a picture while someone is looking at the info screen.
// A port with a live signal would be picked by the monitor whenever the active input
// sleeps (Auto Input Switch or "no signal" search), and keeps it from going to standby.
// DDC/CI works either way.
void screenVideo(bool on);   // on: picture for SCREEN_TIMEOUT_MS, then off again
bool screenVideoOn();

bool screenSize(int& w, int& h);   // false (0 x 0) without video
void screenDump(Print& out);       // framebuffer as "#<hex>" lines, one per pixel row
