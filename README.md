# CZBX
CZBX is an interactive command line tool for Zabbix to get the "Problems" overview inside your terminal!

## Supported platforms
At the moment it is only tested on Ubuntu 22.04 with Python 3.11 and Zabbix 6.4.

## Installing
Either install using pip or similar:
```
python3 -m pip install .
```

Or just follow the usual virtual env way:
```
python3 -m venv env
./env/bin/pip install -r requirements.txt
./env/bin/python3 czbx.py
```

## Getting started
### Authentication
CZBX requires you to use a ZABBIX API token.
Create one by following the [Zabbix documentation](https://www.zabbix.com/documentation/current/en/manual/web_interface/frontend_sections/users/api_tokens)

Specify your Zabbix instance url with `ZABBIX_URL` and your token with `ZABBIX_TOKEN`.
For example put into your `.bashrc`:
```bash
export ZABBIX_URL="https://localhost"
export ZABBIX_TOKEN="XXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
```
and source it: `source ${HOME}/.bashrc`
to start using CZBX.

### Executing SSH on a host
You can press `s` to execute `ssh` towards a highlighted host.
The executed command can be customized with setting the environment variable `$CZBX_SSH_CMD` and it is executed as: `$CZBX_SSH_CMD HOST`.

### Tag filtering
You can specify tags to filter on under: `$USER_CONFDIR/czbx/tags.json`
`$USER_CONFDIR` depends on your platform, for now only Linux is tested, which uses: `$HOME/.config`

Tags are defined for now as described in [Zabbix API problem.get](https://www.zabbix.com/documentation/current/en/manual/api/reference/problem/get).
All tags are AND'ed together.
An example would look like:
```json
[
  { "tag": "Tag is like",      "operator": 0, "value": "something" },
  { "tag": "Tag equal to",     "operator": 1, "value": "something" },
  { "tag": "Tag not like",     "operator": 2, "value": "something" },
  { "tag": "Tag not equal to", "operator": 3, "value": "something" },
  { "tag": "Tag exists",       "operator": 4 },
  { "tag": "Tag not exists",   "operator": 5 }
]
```

## Usage
Just start it with `czbx` or `./env/bin/python czbx.py`.
Make sure `ZABBIX_URL` and `ZABBIX_TOKEN` environment variables are set!

At the moment Zabbix data is not refreshed automatically in the background. Press `r` to refresh it.

## Navigation and Keybindings
Normal navigation via `h,j,k,l` and arrow keys is supported.
For a complete list of key bindings please see:
- `D`: toggle debug output in the status line
- `l`, `right arrow key`: Scroll problem view right
- `h`, `left arrow key`: Scroll problem view left
- `j`, `down arrow key`: Move one line down
- `k`, `up arrow key`: Move one line up
- `0`: scroll problem view to the original position
- `CTRL-F`: move one page down
- `CTRL-B`: move one page up
- `CTRL-L`: redraw screen
- `r`: refresh Zabbix data
- `s`: execute `ssh HOST` or `$CZBX_SSH_CMD HOST` if set. Use HOST on currently highlighted problem
- `o`: open Zabbix problem in webbrowser (Buggy at the moment)
- `c`: copy Zabbix problem URL into clipboard and show the link in status line
- `t`: tag problem (Currently useless)
- `T`: tag all problems with provided substring (Currently useless)
- `CTRL-T`: untag all provided with provided substring. (Currently useless)
- `a`: prompt for acknowledgement message and ack the highlighted problem with it
- `A`: toggle acknowledgement flag on the highlighted problem
- `V`: print current version in status line

## Known issues
- Opening a problem in webbrowser might distort the terminal screen
- Copying to clipboard sometimes fails on WSL
- A lot more I'm not yet aware of :D
