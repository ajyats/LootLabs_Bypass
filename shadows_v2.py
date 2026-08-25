# Made by A.J Yatez
#    - https://trw.lat/ds - MCB 
#    - Version 2 with ""INSTANT"" Solving, fixed issues (it only working with deltax links) n shi - Userscript will be always up to date, install it! https://trw.lat/install/userscript/u.raw.js?v=githubgooning_givmelastversionplesk
#    - Plesk give it a star ily <3
#    - Happy birthday to you fat nigger aka .sentric on discord

import json
import math
import random
import re
import threading
import time
import base64
import hashlib
import ast
import os
import gzip
import zlib
from urllib.parse import urlparse
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import websocket
import requests

TURNSTILE_KEY = "0x4AAAAAAEO6tvECK-X4VCvq"
CAPMONSTER_KEY = "YOUR_CAPMONSTER_KEY" # OR REPLACE THE CAPMONSTER LOGIC WITH THE ONE FROM YOUR SOLVER

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
)


def make_session(hostname): #
    origin = f"https://{hostname}"
    session = requests.Session()
    session.headers.update({
        "User-Agent": DEFAULT_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Sec-CH-UA": '"Chromium";v="139", "Not:A-Brand";v="24", "Google Chrome";v="139"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Origin": origin,
        "Referer": f"https://{hostname}",
    })
    return session


def wildcard_search(text, pattern): #
    regex = re.escape(pattern).replace(r"\*", "(.*?)")
    match = re.search(regex, text)
    return match.group(1) if match else None


def decode_resp(response):
    encoding = (response.headers.get("Content-Encoding") or "").lower()
    content = response.content
    try:
        if "gzip" in encoding:
            return gzip.decompress(content).decode("utf-8")
        if "deflate" in encoding:
            return zlib.decompress(content).decode("utf-8")
        return content.decode("utf-8", errors="ignore")
    except Exception:
        return content.decode("utf-8", errors="ignore")


def cln_url(u):
    return re.sub(r'<.*|".*', '', u)


def ext_info(response, pattern):
    match = re.search(pattern, response)
    return cln_url(match.group(1)) if match else None


def get_cdn_tid(content):
    if not content:
        return (None, None, None)
    cdn = ext_info(content, r"p\['CDN_DOMAIN'\]\s*=\s*'([^']*)'")
    tid = ext_info(content, r"p\['TID'\]\s*=\s*(\d+)")
    key = ext_info(content, r"p\['KEY'\]\s*=\s*\"([^\"]*)\"")
    if cdn and tid and key:
        return (cdn, tid, key)
    return (None, None, None)


def get_p_vars(content):
    pvars = {}
    for m in re.finditer(r"p\['(\w+)'\]\s*=\s*([^\n;]+)", content):
        k, v = m.group(1), m.group(2).strip().rstrip(';').strip()
        if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
            v = v[1:-1]
        pvars[k] = v
    return pvars


def decrypt_data(encoded_data, key_length=5):
    try:
        raw = base64.b64decode(encoded_data)
        key, blob = raw[:key_length], raw[key_length:]
        return bytes(b ^ key[i % key_length] for i, b in enumerate(blob)).decode('utf-8').strip()
    except Exception:
        return encoded_data.strip()


def _ws_proxy_kwargs(session):
    proxy_dict = getattr(session, 'proxies', {}) or {}
    proxy_url = proxy_dict.get('https') or proxy_dict.get('http')
    if not proxy_url:
        return {}
    parsed = urlparse(proxy_url)
    kwargs = {
        'http_proxy_host': parsed.hostname,
        'http_proxy_port': parsed.port or 80,
        'proxy_type': 'http',
    }
    scheme = (parsed.scheme or '').lower()
    if scheme.startswith('socks'):
        kwargs['proxy_type'] = 'socks5' if '5' in scheme else 'socks4'
    if parsed.username and parsed.password:
        kwargs['http_proxy_auth'] = (parsed.username, parsed.password)
    return kwargs


def _ws_header_list(session):
    ua = session.headers.get(
        'User-Agent',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    )
    headers = [
        f'User-Agent: {ua}',
        'Accept-Language: en-US,en;q=0.9',
        'Cache-Control: no-cache',
        'Pragma: no-cache',
    ]
    cookie_str = '; '.join(f'{k}={v}' for k, v in session.cookies.items())
    if cookie_str:
        headers.append(f'Cookie: {cookie_str}')
    return headers


def _fire(fn, *args, **kwargs):
    threading.Thread(target=lambda: _silent(fn, *args, **kwargs), daemon=True).start()


def _silent(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except Exception:
        pass


def _get(session, url, **kw):
    if not url:
        return None
    if url.startswith('//'):
        url = 'https:' + url
    kw.setdefault('timeout', 6)
    kw.setdefault('allow_redirects', True)
    return session.get(url, **kw)


def _beacon_post(session, url):
    if not url:
        return
    if url.startswith('//'):
        url = 'https:' + url
    session.post(url, data=b'', headers={'Content-Type': 'text/plain;charset=UTF-8'}, timeout=4)


def _parse_r_payload(message):
    if not isinstance(message, str) or not message.startswith('r:'):
        return None
    payload = ''.join(ch for ch in message[2:].strip() if 32 <= ord(ch) <= 126)
    if payload.startswith('http://') or payload.startswith('https://'):
        return payload
    return decrypt_data(payload)


def canserbero(session, server, tasks, p_key, tid, session_id, page_origin, done, TLeft=45):
    if not tasks:
        return
    urid = str(tasks[0].get('urid', ''))
    cat = str(tasks[0].get('task_id', 0))
    try:
        shard = int(urid[-5:]) % 3
    except Exception:
        shard = 0
    origin = page_origin if str(page_origin).startswith('http') else f'https://{page_origin}'
    ws_url = (
        f"wss://{shard}.{server}/c?uid={urid}&cat={cat}"
        f"&key={p_key}&session_id={session_id}&is_loot=1&tid={tid}"
    )
    ws = None
    ping_stop = threading.Event()
    try:
        ws = websocket.create_connection(
            ws_url,
            timeout=8,
            header=_ws_header_list(session),
            origin=origin,
            **_ws_proxy_kwargs(session),
        )
        ws.settimeout(0.5)

        def _ping():
            while not ping_stop.wait(10):
                try:
                    ws.send("0")
                except Exception:
                    return

        threading.Thread(target=_ping, daemon=True).start()
        deadline = time.time() + max(int(TLeft or 30), 10)
        while time.time() < deadline and not done.get("result"):
            try:
                message = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                break
            if isinstance(message, bytes):
                try:
                    message = message.decode('utf-8')
                except Exception:
                    continue
            if message == 'Refresh Page':
                break
            result = _parse_r_payload(message)
            if result:
                done["result"] = result
                return
    except Exception:
        return
    finally:
        ping_stop.set()
        if ws:
            try:
                ws.close()
            except Exception:
                pass


def transform_uuid(uuid_str):
    m = re.findall(r'[A-Z]', uuid_str)
    key_str = ''.join(m[:4]) if m else 'KEY1'
    uuid_bytes = uuid_str.encode('utf-8')
    key_bytes = key_str.encode('utf-8')
    xored = bytes(uuid_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(uuid_bytes)))
    return base64.b64encode(xored).decode('ascii')


def _fract(r6, n1):
    n_ = 43758.5453 * math.sin(12.9898 * r6 + 78.233 * n1)
    return n_ - math.floor(n_)


def solve_webgl_nonce(uuid_str):
    y6 = int(uuid_str.replace('-', '')[:8], 16) / 4294967295.0
    for nonce in range(100000):
        o4 = _fract(y6, nonce)
        o4 = _fract(o4, nonce + 1)
        o4 = _fract(o4, nonce + 2)
        if o4 < 0.001:
            return nonce
    return 99999


def make_botd(session_uuid):

    nonce = solve_webgl_nonce(session_uuid) # tbh i didn't see this before in the last version - WebGL PoW, thats why it was failing
    # What I’m wondering is, why did the previous bypasser without PoW let you bypass Deltax links but not links from other services? 
    # It honestly seems intentional, because why would you check PoW on every link except those from one specific creator? 
    # Either their system is shit, or they’re hiding some shit here

    solve_time = int(nonce * random.uniform(1.15, 1.4) + random.randint(20, 80))
    botd = {
        "bot": False,
        "timestamp": int(time.time() * 1000),
        "webGLSolution": {
            "uuid": session_uuid,
            "nonce": nonce,
            "time": solve_time,
        },
    }
    aes_key = hashlib.sha256(transform_uuid(session_uuid).encode('utf-8')).digest()
    iv = os.urandom(12)
    plaintext = json.dumps(botd, separators=(",", ":")).encode('utf-8')
    ct = AESGCM(aes_key).encrypt(iv, plaintext, None)
    botd["encrypted"] = base64.b64encode(iv + ct).decode('ascii')
    return json.dumps(botd, separators=(",", ":"))


def getParameters(raw_string):
    text = (raw_string or "").strip()
    try:
        data = json.loads('[' + text[1:-2] + ']')
    except Exception:
        if text.endswith(';'):
            text = text[:-1]
        text = text.replace('false', 'False').replace('true', 'True').replace('null', 'None')
        data = ast.literal_eval(text)
    return {
        "websocket_domain": data[9],
        "websocket_backup": data[10],
        "websocket_bckup2": data[11],
        "tc_domain": data[29],
        "allow_unlocker": data[30],
    }


def solve_turnstile(origin, cdata=None, action=None):
    # REPLACE THIS WITH YOUR OWN TURNSTILE SOLVER LOGIC OR CAPTCHA SOLVER PROVIDER
    task = {"type": "TurnstileTask", "websiteURL": origin, "websiteKey": TURNSTILE_KEY}
    if cdata:
        task["data"] = cdata
    if action:
        task["pageAction"] = action
    create = requests.post(
        "https://api.capmonster.cloud/createTask",
        json={"clientKey": CAPMONSTER_KEY, "task": task},
        timeout=15,
    ).json()
    if create.get("errorId") != 0:
        raise Exception(create.get("errorCode") or create)
    task_id = create["taskId"]
    while True:
        res = requests.post(
            "https://api.capmonster.cloud/getTaskResult",
            json={"clientKey": CAPMONSTER_KEY, "taskId": task_id},
            timeout=15,
        ).json()
        if res.get("errorId") != 0:
            raise Exception(res.get("errorCode") or res)
        if res.get("status") == "ready":
            return res["solution"]["token"]
        time.sleep(0.4)


def _as_bool(v, default=True):
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("1", "true")
    return bool(v)


def OG_getDest(url, verbose_cb=None):
    # verbose_cb is a parameter for TRW-API - maybe you can use it for your own project
    # why its still here? i told Grok to rewrite the code without CF_Boom / Internal APIs so y'all can run it on raw python
    # i didn't skid with grok btw, it made the original code and got it working, it just removed cfboom api calls n shi
    vcb = verbose_cb or (lambda msg: None)
    hostname = urlparse(url).hostname
    session = None
    t0 = time.perf_counter()

    def taken():
        return f"{time.perf_counter() - t0:.2f}s"

    try:
        vcb(f"Obtaining AdMaven/LootLabs session for {hostname}...")
        session = make_session(hostname)
        origin = f"https://{hostname}"

        initial = session.get(url, headers={"Origin": origin}, timeout=15)
        sess_uuid = wildcard_search(initial.text, "<script>document.session = '*'</script>")
        if not sess_uuid:
            return f'bypass fail! Session UUID not found ({taken()})'
        vcb("Session UUID obtained")

        _fire(
            session.post,
            f"{origin}/verify",
            data=json.dumps({"session": sess_uuid}, separators=(",", ":")),
            headers={"Content-Type": "text/plain;charset=UTF-8", "Origin": origin},
            timeout=6,
        )

        cdn, tid, key = get_cdn_tid(initial.text)
        if not all([cdn, tid, key]):
            return f'bypass fail! CDN/TID/KEY not found ({taken()})'
        vcb("CDN parameters extracted")

        pvars = get_p_vars(initial.text)
        content_resp = session.get(
            f'https://{cdn}/?tid={tid}&params_only=1',
            headers={"Origin": origin},
            timeout=10,
        )
        params = getParameters(decode_resp(content_resp))

        mess_session = str(random.randint(1, 9)) + ''.join(str(random.randint(0, 9)) for _ in range(16)) + str(random.randint(0, 9))
        try:
            test_unl = int(pvars.get("TEST_UNLOCKER_APP", -1))
        except Exception:
            test_unl = -1
        try:
            unlocker_only = int(pvars.get("UNLOCKER_ONLY", "0"))
        except Exception:
            unlocker_only = 0

        TCData = {
            "tid": int(tid),
            "bl": [18, 2, 33, 7, 21, 49],
            "session": mess_session,
            "max_tasks": 1,
            "design_id": 135,
            "cur_url": url,
            "doc_ref": "",
            "tier_id": "0",
            "num_of_tasks": "1",
            "is_loot": True,
            "rkey": key,
            "cookie_id": str(random.randint(100000000, 999999999)),
            "botd": make_botd(sess_uuid),
            "botds": sess_uuid,
            "offer": pvars.get("OFFER", "0"),
            "ver": pvars.get("WIDGET_VERSION") or "v1",
            "tasks_timer": pvars.get("TASKS_TIMER") or "-1",
            "test_unlocker_app": test_unl,
            "allow_unlocker": _as_bool(params.get("allow_unlocker"), True),
            "show_unlocker": _as_bool(pvars.get("SHOW_UNLOCKER"), True),
            "desktop_design": 1 if pvars.get("DESKTOP_DESIGN") in ('1', 'true') else 0,
            "unlocker_only": unlocker_only,
            "additional_info": {},
            "taboola_user_sync": "0",
        }

        SYNCER = params.get("tc_domain") or "nerventualken.com"
        vcb("Posting task config to sync server...")
        saved_headers = dict(session.headers)
        try:
            session.headers.clear()
            session.headers.update({
                "User-Agent": saved_headers.get("User-Agent", ""),
                "Accept": "*/*",
                "Accept-Language": saved_headers.get("Accept-Language", "en-US,en;q=0.9"),
                "Content-Type": "application/json",
                "Origin": origin,
                "Referer": f"{origin}/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site",
            })
            rawr = session.post(f'https://{SYNCER}/tc', json=TCData, timeout=15)
        finally:
            session.headers.clear()
            session.headers.update(saved_headers)

        if rawr.status_code != 200:
            return f'bypass fail! TC status {rawr.status_code} ({taken()})'

        TCP = json.loads(decode_resp(rawr))
        TCP_list = TCP if isinstance(TCP, list) else [TCP]
        if not TCP_list:
            return f'bypass fail! Empty TC response ({taken()})'
        TCP = TCP_list[0]

        captcha_task = next(
            (i for i in TCP_list if i.get("title") == "Confirm you are human" or str(i.get("task_id")) == "41"),
            None,
        )
        bind = captcha_task or TCP
        urid = bind.get("urid")
        task_id = bind.get("task_id", 0)
        if not urid:
            return f'bypass fail! No urid ({taken()})'
        vcb(f"urid={urid} task_id={task_id}")

        ws_session = bind.get("session_id") or "undefined"
        ws_domain = params.get("websocket_domain") or "onsultingco.com"
        try:
            shard = int(str(urid)[-5:]) % 3
        except Exception:
            shard = 0
        shard_host = f"{shard}.{ws_domain}"

        for idx, item in enumerate(TCP_list):
            _fire(_get, session, f"https://enaightdecipie.com/?event=task_clicked&session_id={item.get('task_id')}&info={idx + 1}")

        done = {"result": None}
        vcb("Connecting to WebSocket for result...")
        ws_thread = threading.Thread(
            target=canserbero,
            args=(session, ws_domain, [bind], key, tid, ws_session, origin, done),
            kwargs={"TLeft": 40},
            daemon=True,
        )
        ws_thread.start()

        _fire(_beacon_post, session, f"https://{shard_host}/st?uid={urid}&cat={task_id}")
        ap = bind.get("action_pixel_url") or TCP.get("action_pixel_url")
        if ap:
            _fire(_get, session, ap)
        _fire(_get, session, f"https://{SYNCER}/td?ac=auto_complete&urid={urid}&cat={task_id}&tid={tid}")

        if captcha_task:
            cap_url = captcha_task.get("ad_url") or f"https://{SYNCER}/captcha?urid={urid}"
            if not str(cap_url).startswith("http"):
                cap_url = f"https://{SYNCER}/captcha?urid={urid}"
            vcb("Solving turnstile...")
            cap_html = ""
            try:
                cap_resp = session.get(cap_url, headers={"Referer": f"{origin}/"}, timeout=8)
                cap_html = cap_resp.text
            except Exception:
                pass
            cdata = wildcard_search(cap_html, 'data-cdata="*"') if cap_html else None
            actin = None
            if cap_html:
                actin = wildcard_search(cap_html, 'data-action="*"') or wildcard_search(cap_html, 'action="*"')

            token = solve_turnstile(cap_url, cdata, actin)
            vrf = session.post(
                f"https://{SYNCER}/captcha/verify",
                json={"urid": str(urid), "token": token},
                headers={
                    "Origin": f"https://{SYNCER}",
                    "Referer": cap_url,
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            vcb(f"Captcha verify {vrf.status_code}")
            _fire(_get, session, f"https://{SYNCER}/td?ac=captcha&urid={urid}&=&cat={task_id}&tid={tid}")

        ws_thread.join(timeout=20)
        if done["result"]:
            elapsed = taken()
            vcb(f"AdMaven/LootLabs paywall bypassed via WebSocket  time taken: {elapsed}")
            print(f"time taken: {elapsed}")
            return done["result"]

        return f'bypass fail! All WS candidates failed ({taken()})'

    except Exception as e:
        return f'bypass fail! {e} ({taken()})'
    finally:
        if session:
            try:
                session.close()
            except Exception:
                pass


def getDest(url, verbose_cb=None):
    return OG_getDest(url, verbose_cb=verbose_cb)



target = "https://links.lootlabs.gg/s?2j2wXWWH" # new link yay
print(getDest(target, verbose_cb=print))
