#ifndef __TM1637_H__
#define __TM1637_H__

#define N_TM1637 4
#define N_7SEG 6

extern uint8_t tm1637_buffer[N_TM1637 * N_7SEG];
void tm1637_init();
void tm1637_send();

#endif // __TM1637_H__