import curses

def show_help():
   popup = curses.newwin(20, 60, curses.LINES//2-10, curses.COLS//2-30)
   popup.box()
   popup.addstr(0, 4, "CZBX help")
   popup.addstr(18, 37, 'Press q or ? to close')

   keybindings = [
       "   up, k  Move cursor up",
       " down, j  Move cursor down",
       "right, l  Scoll right",
       " left, h  Scoll left",
       "       0  Scroll to start position",
       "  CTRL-F  Move one page down",
       "  CTRL-B  Move one page up",
       "  CTRL-L  Redraw screen",
       "       s  Execute CZBX_SSH_CMD on HOST",
       "       o  Open problem in webbrowser",
       "       c  Copy problem url into clipboard",
       "       t  Tag problem",
       "       T  Tag problems matching PATTERN",
       "  CTRL-T  Untag problems matching PATTERN",
       "       a  Ack problem with message",
       "       A  Toggle ack flag on problem",
       "       V  Print version",
       "       ?  Show help",
       "       q  Quit CZBX",
   ]

   s=0
   while True:
       e=s+15
       for y, keybinding in enumerate(keybindings[s:e], start=2):
           popup.addstr(y, 2, " "*57)
           popup.addstr(y, 2, keybinding)
       if e >= len(keybindings):
           popup.addstr(y+1, 25, "          ")
       else:
           popup.addstr(17, 25, "-- more --")
       key = popup.getkey()
       match key:
           case 'q' | '?': break
           case 'j': s = min(s+1, len(keybindings)-15)
           case 'k': s = max(s-1, 0)

   popup.erase()
