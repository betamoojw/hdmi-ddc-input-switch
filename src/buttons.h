// Keys from config: debounced, fire once on press, no repeat while held.
#pragma once
#include <Arduino.h>

void buttonsBegin();                 // (re)configure pins from config
int  buttonsPoll();                  // index of a key just pressed, or -1
bool buttonsResetHeld();             // keys 1 and 2 held at power-up (factory reset)
