// Info screen on the Feather's own HDMI output (80x30 text, PicoDVI). The monitor
// shows it when switched to the input the switch is plugged into. Content comes from
// `config` and `status`. Build with -D DISABLE_VIDEO to leave the port without a picture.
#pragma once
#include <Arduino.h>

bool screenBegin();    // false if video failed to start
void screenDraw();     // full redraw
void screenTick();     // cheap refresh of the changing lines (times, last command)
