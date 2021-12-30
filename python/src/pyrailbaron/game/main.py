import pygame as pg

SCREENRECT = pg.Rect(0,0,800,480)

def main():
    pg.init()
    bestdepth = pg.display.mode_ok(SCREENRECT.size, 0, 32)
    pg.display.set_mode(SCREENRECT.size, 0, bestdepth)

    clock = pg.time.Clock()

    while True:
        if any(event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_q)
            for event in pg.event.get()):
                break
        clock.tick(40)
    pg.quit()