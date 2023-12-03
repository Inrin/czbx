import argparse
import curses
from datetime import datetime
import subprocess
import os
import webbrowser

import pyperclip
import pyzabbix

from .help import show_help
from .zabbix import ZabbixData, _init_zabbix
from .colors import _init_colors

__VERSION__ = "0.1.1"


def _parse_args():
    parser = argparse.ArgumentParser(description="Curses Zabbix Problems UI")

    parser.add_argument("-u", "--zabbix-url", help="Zabbix URL")
    parser.add_argument("-s", "--ssh-cmd", help="SSH command to execute")

    args = parser.parse_args()

    args.zabbix_url = os.getenv("ZABBIX_URL", args.zabbix_url)
    args.ssh_cmd = os.getenv("CZBX_SSH_CMD", args.ssh_cmd)

    return args


def _start_curses(stdscr, args):
    _init_colors()
    curses.curs_set(0)

    stdscr.addnstr(
        0,
        0,
        "CZBX - Problems Overview " + " " * curses.COLS,
        curses.COLS,
        curses.A_STANDOUT,
    )
    stdscr.addstr(curses.LINES - 1, 0, "Loading Zabbix data")
    stdscr.refresh()

    zbx = _init_zabbix()
    debug = False
    status_line = None

    def update_content(y, x, lineno, status_line, tagged_lines):
        content.move(0, 0)
        for idx, problem in enumerate(zbx_data.problems):
            attrs = 0
            trigger = zbx_data.triggers[problem["objectid"]]
            if idx == lineno:
                attrs |= curses.A_STANDOUT
            time = (
                datetime.fromtimestamp(int(problem["clock"]))
                .isoformat()
                .removeprefix(f"{datetime.now():%Y-%m-%dT}")
                .replace("T", " ")
            )
            scolor = int(problem["severity"])
            severity = ["None", "Info", "Warning", "Average", "High", "Disaster"][
                scolor
            ]
            rtime = int(problem["r_clock"])
            rtime = f"{datetime.fromtimestamp(rtime):%H:%M:%S}" if rtime else ""
            status = "RESOLVED" if rtime else "PROBLEM"
            problem_name = problem["name"]
            acked = "✔" if problem["acknowledged"] == "1" else ""
            if problem["acknowledged"] == "1":
                attrs |= curses.A_DIM
            tagged = "*" if idx in tagged_lines else " "
            content.addstr(
                f"{tagged}{acked:<1} {time: >19} ", attrs | curses.color_pair(103)
            )
            if status == "RESOLVED":
                content.addstr(f"{severity:<8}", attrs)
            else:
                content.addstr(
                    f"{severity:<8}",
                    attrs | curses.A_REVERSE | curses.color_pair(scolor),
                )
            host = trigger["hosts"][0]["name"]
            content.attroff(curses.A_REVERSE)
            content.addstr(f" {rtime: >8}", attrs | curses.color_pair(103))
            pcolor = 102 if status == "RESOLVED" else 101
            content.addstr(f" {status:<9}", attrs | curses.color_pair(pcolor))
            content.addstr(f"{host:<{zbx_data.max_hostname}} {problem_name}\n", attrs)

        opdata = (
            ", ".join(
                f"{i['lastvalue']}{' '+i['units'] if i['units'] else ''}"
                for i in zbx_data.triggers[zbx_data.problems[lineno]["objectid"]][
                    "items"
                ]
            )
            if len(zbx_data.problems)
            else ""
        )
        stdscr.addstr(0, 30, f"{opdata}", curses.A_STANDOUT)
        stdscr.clrtoeol()
        stdscr.chgat(0, 0, curses.A_STANDOUT)
        if status_line:
            stdscr.addstr(curses.LINES - 1, 0, status_line)
        elif debug:
            content_len = len(zbx_data.problems)
            pages = int(content_len / (curses.LINES - 2)) + 1
            page = lineno // (curses.LINES - 2) + 1
            stdscr.addstr(
                curses.LINES - 1,
                0,
                f"X: {xpos} Y: {ypos} CL: {content_len} COLS: {curses.COLS} LINES: {curses.LINES}, LINE: {lineno}, PAGE: {page}/{pages}",
            )
        else:
            tags = len(zbx_data.problems) and zbx_data.problems[lineno]["tags"] or []
            stdscr.addnstr(
                curses.LINES - 1,
                0,
                " | ".join(f"{t['tag']}:{t['value']}" for t in tags),
                curses.COLS - 1,
            )
        stdscr.clrtoeol()

        content.refresh(y, x, 1, 0, curses.LINES - 2, curses.COLS - 1)

    xpos = 0
    ypos = 0
    lineno = 0
    tagged_lines = []
    zbx_data = ZabbixData(zbx)
    content = curses.newpad(len(zbx_data.problems) + 1024, 8096)
    update_content(ypos, xpos, lineno, status_line, tagged_lines)

    stdscr.timeout(30000)
    while True:
        update_zbx_data = False
        status_line = None

        try:
            key = stdscr.getkey()
        except curses.error:
            key = None
            update_zbx_data = True

        match key:
            case "q":
                break
            case "KEY_RESIZE":
                curses.update_lines_cols()
            case "D":
                debug = not debug
            case "l" | "KEY_RIGHT":
                xpos = min(8095, xpos + 1)
            case "h" | "KEY_LEFT":
                xpos = max(0, xpos - 1)
            case "j" | "KEY_DOWN":
                lineno = min(lineno + 1, len(zbx_data.problems) - 1)
                page_before = (lineno - 1) // (curses.LINES - 2) + 1
                page_after = (lineno) // (curses.LINES - 2) + 1
                if page_before != page_after:
                    lineno = max(0, lineno - curses.LINES + 2)
                    curses.unget_wch("")
            case "k" | "KEY_UP":
                lineno = max(0, lineno - 1)
                page_before = (lineno + 1) // (curses.LINES - 2) + 1
                page_after = (lineno) // (curses.LINES - 2) + 1
                if page_before != page_after:
                    ypos = max(0, ypos - curses.LINES + 2)
            case "0":
                xpos = 0
            case "":
                if ypos + curses.LINES - 2 < len(zbx_data.problems):
                    ypos = ypos + curses.LINES - 2
                    lineno = min(len(zbx_data.problems) - 1, lineno + curses.LINES - 2)
            case "":
                ypos = max(0, ypos - curses.LINES + 2)
                lineno = max(0, lineno - curses.LINES + 2)
            case "":
                stdscr.erase()
                stdscr.addnstr(
                    0,
                    0,
                    "CZBX - Problems Overview " + " " * curses.COLS,
                    curses.COLS,
                    curses.A_STANDOUT,
                )
                content.erase()
                stdscr.refresh()
            case "r":
                update_zbx_data = True
            case "s":
                host = zbx_data.triggers[zbx_data.problems[lineno]["objectid"]][
                    "hosts"
                ][0]["name"]
                curses.endwin()
                subprocess.run(f"{args.ssh_cmd} {host}", shell=True)
                curses.initscr()
            case "o":
                _url = args.zabbix_url
                curses.endwin()
                webbrowser.open(
                    f"{_url}/tr_events.php?triggerid={zbx_data.problems[lineno]['objectid']}&eventid={zbx_data.problems[lineno]['eventid']}"
                )
                curses.initscr()
                stdscr.clear()
                stdscr.addnstr(
                    0,
                    0,
                    "CZBX - Problems Overview " + " " * curses.COLS,
                    curses.COLS,
                    curses.A_STANDOUT,
                )
                content.clear()
            case "c":
                _url = args.zabbix_url
                url = f"{_url}/tr_events.php?triggerid={zbx_data.problems[lineno]['objectid']}&eventid={zbx_data.problems[lineno]['eventid']}"
                curses.endwin()
                pyperclip.copy(url)
                curses.initscr()
                status_line = f"Copied {url}"
            case "t":
                content.move(lineno, 0)
                if lineno in tagged_lines:
                    tagged_lines.remove(lineno)
                    content.echochar(" ")
                else:
                    tagged_lines.append(lineno)
                    content.echochar("*")
                curses.unget_wch("j")
            case "T":
                stdscr.addstr(curses.LINES - 1, 0, "Tag problems matching: ")
                stdscr.clrtoeol()
                curses.echo()
                pattern = stdscr.getstr().decode("utf8")
                curses.noecho()
                content.move(lineno, 0)
                content.echochar("*")
                for idx, p in enumerate(zbx_data.problems):
                    if pattern in p["name"]:
                        tagged_lines.append(idx)
            case "":
                stdscr.addstr(curses.LINES - 1, 0, "Untag problems matching: ")
                stdscr.clrtoeol()
                curses.echo()
                pattern = stdscr.getstr().decode("utf8")
                curses.noecho()
                content.move(lineno, 0)
                content.echochar(" ")
                for idx, p in enumerate(zbx_data.problems):
                    if pattern in p["name"]:
                        tagged_lines.remove(idx)
            case "A":
                problem = zbx_data.problems[lineno]
                if problem["acknowledged"] == "1":
                    zbx.event.acknowledge(eventids=problem["eventid"], action=16)
                    status_line = f"Unacknowledge {problem['eventid']}"
                else:
                    zbx.event.acknowledge(eventids=problem["eventid"], action=2)
                    status_line = f"Acknowledge {problem['eventid']}"
                update_zbx_data = True
            case "a":
                stdscr.addstr(curses.LINES - 1, 0, "ACK Message: ")
                stdscr.clrtoeol()
                curses.echo()
                msg = stdscr.getstr().decode("utf8")
                curses.noecho()
                if msg == "":
                    status_line = "Aborted…"
                else:
                    zbx.event.acknowledge(
                        eventids=zbx_data.problems[lineno]["eventid"],
                        action=6,
                        message=msg,
                    )
                update_zbx_data = True
            case "V":
                status_line = __VERSION__
            case "?":
                show_help()

        if (
            update_zbx_data
            or (datetime.now() - zbx_data.last_updated).total_seconds() >= 30.0
        ):
            status_line = "Fetching data…"
            update_content(ypos, xpos, lineno, status_line, tagged_lines)
            zbx_data.fetch_data()
        update_content(ypos, xpos, lineno, status_line, tagged_lines)


def main() -> None:
    """Starts curses ui"""
    args = _parse_args()
    curses.wrapper(_start_curses, args)
