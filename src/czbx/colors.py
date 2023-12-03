import curses


def _init_colors():
    curses.start_color()
    curses.use_default_colors()
    rgb = lambda r, g, b: (r * 1000 // 255, g * 1000 // 255, b * 1000 // 255)
    curses.init_color(2, *rgb(255, 200, 89))
    curses.init_color(3, *rgb(255, 160, 89))
    curses.init_color(4, *rgb(233, 118, 89))
    curses.init_color(5, *rgb(228, 89, 89))
    curses.init_color(101, *rgb(198, 40, 40))
    curses.init_color(102, *rgb(102, 187, 106))
    curses.init_color(103, *rgb(71, 150, 196))
    curses.init_pair(0, 0, -1)
    curses.init_pair(1, 1, -1)
    curses.init_pair(2, 2, -1)
    curses.init_pair(3, 3, -1)
    curses.init_pair(4, 4, -1)
    curses.init_pair(5, 5, -1)
    curses.init_pair(101, 100, -1)
    curses.init_pair(102, 102, -1)
    curses.init_pair(103, 103, -1)
