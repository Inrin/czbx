import os
import json
from datetime import datetime

import platformdirs
import pyzabbix


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
            and all(
                map(lambda x: x["status"] == "0", self.triggers[p["objectid"]]["items"])
            )
        ]

        self.max_hostname = self.triggers and max(map(len, self.triggers.values())) or 0
