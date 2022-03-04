#ifndef __TM1637_H__
#define __TM1637_H__

class TM1637 {
public:
    TM1637(uint8_t n_displays, uint8_t n_bytes_per_display, 
           uint8_t clk_pin, const uint8_t* dio_pins);
    void begin(void);
    void setByte(uint8_t display_i, uint8_t byte_i, uint8_t value);
    void show(void);
    int busy(void);
private:
    static uint8_t n_displays;
    static uint8_t n_bytes_per_display;
    static uint8_t clk_pin;
    static const uint8_t* dio_pins;
};

#define N_TM1637 4
#define N_7SEG 6

extern uint8_t tm1637_buffer[N_TM1637 * N_7SEG];
void tm1637_init();
void tm1637_send();

#endif // __TM1637_H__