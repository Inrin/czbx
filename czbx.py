#!/usr/bin/env python3

import curses
import json
from datetime import datetime
import subprocess
import os
import sys
import webbrowser

import platformdirs
import pyperclip
import pyzabbix

from help import show_help

__VERSION__ = "0.0.1"


class ZabbixData:

    def __init__(self, api: pyzabbix.ZabbixAPI):
        self.zbx = api
        self.tags = self._load_tags()
        self.fetch_data()

    def _load_tags(self):
        try:
            with open(
                platformdirs.user_config_path("czbx").joinpath("tags.json"),
                "rt",
                encoding="utf8",
            ) as tagfile:
                tags = json.load(tagfile)
        except FileNotFoundError:
            tags = []
        return tags


    def fetch_data(self):
        self.last_updated = datetime.now()

        problems = self.zbx.problem.get(
            recent=True,
            severities=[3, 4, 5],
            sortfield="eventid",
            sortorder="DESC",
            suppressed=False,
            tags=self.tags,
            selectTags="extend",
            time_from=int(datetime.now().timestamp() / 60 / 60 / 24 / 365 / 2),
        )
        self.triggers = {
            t["triggerid"]: t
            for t in self.zbx.trigger.get(
                triggerids=[i["objectid"] for i in problems],
                selectHosts=["name", "status"],
                selectItems=["status", "lastvalue", "units"],
            )
        }
        self.problems = [
            p
            for p in problems
            if self.triggers[p["objectid"]]["status"] == "0"
            and self.triggers[p["objectid"]]["hosts"][0]["status"] == "0"
            and all(map(lambda x: x["status"] == "0", self.triggers[p["objectid"]]["items"]))
        ]

        self.max_hostname = self.triggers and max(map(len, self.triggers.values())) or 0


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


def _init_zabbix():
    _url = os.getenv("ZABBIX_URL")
    _token = os.getenv("ZABBIX_TOKEN")
    if not _url:
        sys.exit("No ZABBIX_URL in ENVs!")
    if not _token:
        sys.exit("No ZABBIX_TOKEN in ENVs!")

    api = pyzabbix.ZabbixAPI(_url)
    api.login(api_token=_token)
    try:
        api.user.checkAuthentication(token=_token)
    except pyzabbix.api.ZabbixAPIException as ex:
        if ex.error["code"] == -32602:
            sys.exit("Not Authorized. Check your ZABBIX_TOKEN and ZABBIX_URL")
        else:
            sys.exit(ex.error)

    return api


def _start_curses(stdscr):
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
    description = False
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
                for i in zbx_data.triggers[zbx_data.problems[lineno]["objectid"]]["items"]
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

        if key == "q":
            break
        elif key == "KEY_RESIZE":
            curses.update_lines_cols()
        elif key == "D":
            debug = not debug
        elif key in ["l", "KEY_RIGHT"]:
            xpos = min(8095, xpos + 1)
        elif key in ["h", "KEY_LEFT"]:
            xpos = max(0, xpos - 1)
        elif key in ["j", "KEY_DOWN"]:
            lineno = min(lineno + 1, len(problems) - 1)
            page_before = (lineno - 1) // (curses.LINES - 2) + 1
            page_after = (lineno) // (curses.LINES - 2) + 1
            if page_before != page_after:
                lineno = max(0, lineno - curses.LINES + 2)
                curses.unget_wch("")
        elif key in ["k", "KEY_UP"]:
            lineno = max(0, lineno - 1)
            page_before = (lineno + 1) // (curses.LINES - 2) + 1
            page_after = (lineno) // (curses.LINES - 2) + 1
            if page_before != page_after:
                ypos = max(0, ypos - curses.LINES + 2)
        elif key == "0":
            xpos = 0
        elif key == "":
            if ypos + curses.LINES - 2 < len(problems):
                ypos = ypos + curses.LINES - 2
                lineno = min(len(problems) - 1, lineno + curses.LINES - 2)
        elif key == "":
            ypos = max(0, ypos - curses.LINES + 2)
            lineno = max(0, lineno - curses.LINES + 2)
        elif key == "":
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
        elif key == "r":
            zbx_data.fetch_data()
        elif key == "s":
            host = triggers[problems[lineno]["objectid"]]["hosts"][0]["name"]
            ssh_cmd = os.getenv("CZBX_SSH_CMD", "ssh")
            curses.endwin()
            subprocess.run(f"{ssh_cmd} {host}", shell=True)
            curses.initscr()
        elif key == "o":
            _url = os.getenv("ZABBIX_URL")
            curses.endwin()
            webbrowser.open(
                f"{_url}/tr_events.php?triggerid={problems[lineno]['objectid']}&eventid={problems[lineno]['eventid']}"
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
        elif key == "c":
            _url = os.getenv("ZABBIX_URL")
            url = f"{_url}/tr_events.php?triggerid={problems[lineno]['objectid']}&eventid={problems[lineno]['eventid']}"
            curses.endwin()
            pyperclip.copy(url)
            curses.initscr()
            status_line = f"Copied {url}"
        elif key == "t":
            content.move(lineno, 0)
            if lineno in tagged_lines:
                tagged_lines.remove(lineno)
                content.echochar(" ")
            else:
                tagged_lines.append(lineno)
                content.echochar("*")
            curses.unget_wch("j")
        elif key == "T":
            stdscr.addstr(curses.LINES - 1, 0, "Tag problems matching: ")
            stdscr.clrtoeol()
            curses.echo()
            pattern = stdscr.getstr().decode("utf8")
            curses.noecho()
            content.move(lineno, 0)
            content.echochar("*")
            for idx, p in enumerate(problems):
                if pattern in p["name"]:
                    tagged_lines.append(idx)
        elif key == "":
            stdscr.addstr(curses.LINES - 1, 0, "Untag problems matching: ")
            stdscr.clrtoeol()
            curses.echo()
            pattern = stdscr.getstr().decode("utf8")
            curses.noecho()
            content.move(lineno, 0)
            content.echochar(" ")
            for idx, p in enumerate(problems):
                if pattern in p["name"]:
                    tagged_lines.remove(idx)
        elif key == "A":
            problem = problems[lineno]
            if problem["acknowledged"] == "1":
                zbx.event.acknowledge(eventids=problem["eventid"], action=16)
                status_line = f"Unacknowledge {problem['eventid']}"
            else:
                zbx.event.acknowledge(eventids=problem["eventid"], action=2)
                status_line = f"Acknowledge {problem['eventid']}"
            zbx_data.fetch_data()
        elif key == "a":
            stdscr.addstr(curses.LINES - 1, 0, "ACK Message: ")
            stdscr.clrtoeol()
            curses.echo()
            msg = stdscr.getstr().decode("utf8")
            curses.noecho()
            if msg == "":
                status_line = "Aborted…"
            else:
                zbx.event.acknowledge(
                    eventids=problems[lineno]["eventid"], action=6, message=msg
                )
            zbx_data.fetch_data()
        elif key == "V":
            status_line = __VERSION__
        elif '?':
            show_help()

        if update_zbx_data or (datetime.now() - zbx_data.last_updated).total_seconds() >= 30.0:
            status_line = "Fetching data…"
            update_content(ypos, xpos, lineno, status_line, tagged_lines)
            zbx_data.fetch_data()
        update_content(ypos, xpos, lineno, status_line, tagged_lines)


def main():
    curses.wrapper(_start_curses)


if __name__ == "__main__":
    main()
