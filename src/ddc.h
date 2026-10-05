// DDC/CI over the HDMI port's I2C lines. Transport only; what to send comes from config.
#pragma once
#include <Arduino.h>

static const uint8_t DDC_ADDR  = 0x37;   // DDC/CI (0x6E write address)
static const uint8_t EDID_ADDR = 0x50;

// "Set VCP feature": [src, 0x84, 0x03, vcp, value hi, value lo, checksum]
// where checksum = 0x6E XOR every preceding byte. Returns true on ACK.
bool ddcSetVcp(uint8_t src, uint8_t vcp, uint16_t value);

// Addresses that ACK; returns the count written to `found`.
uint8_t ddcScan(uint8_t* found, uint8_t max);
