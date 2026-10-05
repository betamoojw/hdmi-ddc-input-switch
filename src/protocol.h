// Serial protocol (115200). One JSON object per line for the web configurator, e.g.
//   {"cmd":"get"}  ->  {"ok":true,"config":{...}}
// plus single-key shortcuts for bench testing (1-8 send an input, s scans, ? help).
// Every reply is one JSON line; unsolicited events look like {"event":"key",...}.
#pragma once
#include <Arduino.h>

void protocolPoll();                       // read and handle incoming serial
void protocolEvent(const char* json);      // emit an unsolicited event line
void protocolKeyEvent(uint8_t key, bool ok);
void protocolBootEvent(bool configLoaded, bool factoryReset, bool video);
