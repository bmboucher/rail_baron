#include <Arduino.h>
#include "tm1637.h"

static const uint8_t CLK_PIN = 19;
static const uint8_t DIO_PINS[N_TM1637] = {23,22,21,20};

uint8_t tm1637_buffer[N_TM1637 * N_7SEG];

void tm1637_init() {
    memset(&tm1637_buffer, 0, sizeof(tm1637_buffer));
    
}

void tm1637_send() {

}