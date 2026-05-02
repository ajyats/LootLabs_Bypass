import json
import random
import re
import threading
import time
import os
import base64
import hashlib
import uuid
import requests
import ast
import traceback
from urllib.parse import urlparse

try:
    from NBA import CF_Boom, debug # CF_Boom & Debug.py are not public for now
except:
    import requests
    import zlib
    try:
        import brotli
    except ImportError:
        brotli = None
    class CF_Boom:
        @staticmethod
        def getSession(url, proxy=None, verify=False):
            s = requests.Session()
            if proxy:
                s.proxies = {'http': proxy, 'https': proxy}
            return s
        @staticmethod
        def getResidentialProxy():
            return None
        @staticmethod
        def wildcard_search(text, pattern):
            match = re.search(r"document\.session\s*=\s*['\"]([^'\"]+)['\"]", text)
            return match.group(1) if match else None
        @staticmethod
        def decodeResp(response):
            if not hasattr(response, 'content'):
                return str(response)
            content = response.content
            encoding = response.headers.get('content-encoding', '').lower()
            if encoding == 'br' and brotli is not None:
                content = brotli.decompress(content)
            elif encoding in ('gzip', 'deflate'):
                try:
                    if 'gzip' in encoding:
                        content = zlib.decompress(content, zlib.MAX_WBITS | 32)
                    else:
                        content = zlib.decompress(content)
                except:
                    pass
            return content.decode('utf-8', errors='ignore')
    class Debug:
        def info(self, msg):
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] INFO: {msg}")
        def error(self, msg):
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {msg}")
        def warn(self, msg):
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARN: {msg}")
        def success(self, msg):
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SUCCESS: {msg}")
        def custom(self, *args):
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CUSTOM: {' '.join([str(a) for a in args])}")
    debug = Debug()

from bs4 import BeautifulSoup
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import websocket

def cln_url(u):
    return re.sub(r'<.*|".*', '', u)

def ext_info(response, pattern):
    match = re.search(pattern, response)
    return cln_url(match.group(1)) if match else None

def get_cdn_tid(content, url=None, delay=None):
    try:
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            for script in soup.find_all('script'):
                if script.string and 'domain:' in script.string:
                    cd = re.search(r"cd: ([^']*),", script.string)
                    domain = re.search(r"domain: '([^']*)'", script.string)
                    key = re.search(r"key: '([^']*)'", script.string)
                    if cd and domain and key:
                        return (domain.group(1), cd.group(1), key.group(1), {'active': False})
            cdn = ext_info(content, r"p\['CDN_DOMAIN'\]\s*=\s*'([^']*)'")
            tid = ext_info(content, r"p\['TID'\]\s*=\s*(\d+)")
            key = ext_info(content, r"p\['KEY'\]\s*=\s*\"([^\"]*)\"")
            tir = ext_info(content, r"p\['TIER_ID'\]\s*=\s*['\"]([^'\"]+)['\"];")
            nta = ext_info(content, r"p\['NUM_OF_TASKS'\]\s*=\s*['\"]([^'\"]+)['\"];")
            ofr = ext_info(content, r"p\['OFFER'\]\s*=\s*['\"]([^'\"]+)['\"]") # retarded regex shit here
            if cdn and tid and key:
                return (cdn, tid, key, {'active': True, 'ntasks': nta, 'tier': tir, 'offer': ofr})
        return (None, None, None, {'active': True, 'ntasks': None, 'tier': None, 'offer': None})
    except Exception as e:
        debug.error(f"get_cdn_tid error: {e}")
        return (None, None, None, {'active': True, 'ntasks': None, 'tier': None, 'offer': None})

def decrypt_data(encoded_data, key_length=5):
    try:
        base64_decoded = base64.b64decode(encoded_data)
        key, encrypted_content = base64_decoded[:key_length], base64_decoded[key_length:]
        decrypted_data = bytes(b ^ key[i % key_length] for i, b in enumerate(encrypted_content))
        result = decrypted_data.decode('utf-8').strip()
        return result
    except Exception as e:
        debug.error(f"Decryption error: {e}")
        return encoded_data.strip()

def canserbero(session, server, syncer, urid, p_key, tid, session_id, isLLBS, task_id, TLeft, APUrl):
    catnumber = task_id
    numbers = [int(urid[-5:]) % 3] + [i for i in range(3) if i != int(urid[-5:]) % 3]
    debug.info(f"Trying servers in order: {numbers}")
    proxy_dict = getattr(session, 'proxies', {})
    proxy_url = proxy_dict.get('https') or proxy_dict.get('http')
    proxy_kwargs = {}
    if proxy_url:
        parsed = urlparse(proxy_url)
        proxy_kwargs = {'http_proxy_host': parsed.hostname, 'http_proxy_port': parsed.port or 80}
        if parsed.username and parsed.password:
            proxy_kwargs['http_proxy_auth'] = (parsed.username, parsed.password)
    for nmb in numbers:
        current_server = f"{nmb}.{server}"
        ws = None
        try:
            threading.Thread(target=lambda s=current_server: session.post(f"https://{s}/st?uid={urid}&cat={catnumber}"), daemon=True).start()
        except Exception as e:
            debug.warn(f"Background POST error: {e}")
        try:
            if APUrl:
                threading.Thread(target=lambda: session.get(f"https:{APUrl}", timeout=5), daemon=True).start()
        except Exception as e:
            debug.warn(f"Background GET error: {e}")
        for attempt in range(1, 3):
            try:
                url = f"wss://{current_server}/c?uid={urid}&cat={catnumber}&key={p_key}&session_id={session_id}&is_loot={isLLBS}&tid={tid}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
                cookie_str = '; '.join([f'{k}={v}' for k, v in session.cookies.items()])
                if cookie_str:
                    headers['Cookie'] = cookie_str
                debug.custom("AdMaven", f"WS connecting: {current_server} ({catnumber}) Attempt: {attempt}", "MAGENTA", "🈺")
                ws = websocket.create_connection(url, timeout=10, header=headers, origin=f'https://{urlparse(f"https://{server}").hostname}', **proxy_kwargs)
                debug.custom('AdMaven', f'WS connected: {current_server}', 'GREEN', '🔗')
                ws.settimeout(10)
                ws.send("0")
                max_wait = 20
                start_time = time.time()
                ping_interval = 3
                last_ping = time.time()
                while time.time() - start_time < max_wait:
                    try:
                        ws.settimeout(1)
                        message = ws.recv()
                        if isinstance(message, bytes):
                            message = message.decode('utf-8')
                        if isinstance(message, str) and message.startswith("r:"):
                            payload = message[2:]
                            result = decrypt_data(payload)
                            debug.success(f"Canserbero OK on {current_server}")
                            ws.close()
                            return result
                        else:
                            # keepalive i guess?
                            # pass
                            niggasaki = True
                        last_ping = time.time()
                    except websocket.WebSocketTimeoutException:
                        if time.time() - last_ping >= ping_interval:
                            try:
                                ws.send("0")
                                last_ping = time.time()
                            except Exception as e:
                                break
                        continue
                    except Exception as e:
                        debug.warn(f"WS recv error on {current_server}: {e}")
                        break
                        
                debug.warn(f"No valid response from {current_server} after {max_wait}s") # nñ
            except websocket.WebSocketException as e:
                debug.error(f"WebSocket error attempt {attempt} on {current_server}: {e}")
            except Exception as e:
                debug.error(f"Canserbero error attempt {attempt} on {current_server}: {e}")
            finally:
                if ws:
                    try:
                        ws.close()
                    except:
                        pass
                ws = None
            if attempt == 1:
                time.sleep(0.5)
    debug.error("All servers and attempts exhausted")
    return None

def transform_uuid(uuid_str):
    uppercase = [c for c in uuid_str if c.isupper()]
    key_str = ''.join(uppercase[:4]) if uppercase else 'KEY1'
    uuid_bytes = uuid_str.encode('utf-8')
    key_bytes = key_str.encode('utf-8')
    xor_result = bytes([uuid_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(uuid_bytes))])
    return base64.b64encode(xor_result).decode('utf-8')

def botd_create_frfr_frfr_frfr(session_uuid):
    transformed = transform_uuid(session_uuid)
    aes_key = hashlib.sha256(transformed.encode()).digest()
    iv = os.urandom(12)
    timestamp = int(time.time() * 1000)
    botd = {
        "bot": False,
        "timestamp": timestamp,
        "webGLSolution": {
            "uuid": session_uuid,
            "nonce": random.randint(1, 3000),
            "time": random.randint(100, 5000)
        }
    }
    
    plaintext = json.dumps(botd, separators=(",", ":")).encode()
    encryptor = AESGCM(aes_key)
    ciphertext = encryptor.encrypt(iv, plaintext, None)
    encrypted = base64.b64encode(iv + ciphertext).decode()
    botd["encrypted"] = encrypted
    
    # it cost me at least 3 hours to figure out how wrappedbot was generating the encrypted shit cryptographically
    # all that just to end up making everything open-source so the "anti-hambreados" skids can steal it lmao
    
    # Looks more or less easy but i'm retarded
    
    return json.dumps(botd, separators=(",", ":"))

def getParameters(raw_string):
    if raw_string.strip().endswith(';'):
        raw_string = raw_string.strip()[:-1]
    raw_string = raw_string.replace('false', 'False').replace('true', 'True').replace('null', 'None')
    data = ast.literal_eval(raw_string)
    return {
        "tid": data[0], "backup_domain": data[1], "backup2_domain": data[2], "sixteen_type": data[3],
        "datacloudfront_domain": data[4], "EM_List": data[5], "max_tasks": data[6], "bl_config": data[7],
        "tracking": data[8], "websocket_domain": data[9], "websocket_backup": data[10],
        "websocket_bckup2": data[11], "pixel_enabled": data[12], "redirect_domain": data[13],
        "debug_mode": data[14], "debug_level": data[15], "RGBA_Payloas": data[16],
        "custom_css": data[17], "custom_js": data[18], "cookie_notice": data[19], "theme": data[20],
        "custom_logo": data[21], "maintenance_mode": data[22], "extra_scripts": data[23],
        "extra_styles": data[24], "extra_fonts": data[25], "background_color": data[26],
        "custom_html": data[27], "security_tend": data[28], "tc_domain": data[29],
        "analytics_enabled": data[30], "ads_enabled": data[31]
    } # no real names, i just put random shit here tbh

def OG_getDest(url):
    hostname = urlparse(url).hostname
    try:
        try:
            session = CF_Boom.getSession(f"https://{hostname}", CF_Boom.getResidentialProxy(), False)
        except:
            session = requests.Session() # Works better with a similar browser requests session but yeah you can use requests.Session()
            
        initial = session.get(url, timeout=15)
        sess_uuid = CF_Boom.wildcard_search(initial.text, "<script>document.session = '*'</script>")
        if not sess_uuid:
            return 'bypass fail! Session UUID not found in HTML'
        debug.info(f'Session UUID extracted: {sess_uuid}')
        cdn, tid, key, GisLLBS = get_cdn_tid(initial.text, url, 1)
        if not all([cdn, tid, key]):
            return 'bypass fail! CDN/TID/KEY not found'
        isLLBS = GisLLBS.get('active', False)
        isLLBS_str = '1' if isLLBS else '0'
        
        content = CF_Boom.decodeResp(session.get(f'https://{cdn}/?tid={tid}&params_only=1', timeout=15))
        params = getParameters(content)
        SYNCER = params.get('tc_domain')
        
        if not SYNCER:
            return 'bypass fail! tc_domain not found'
            
        if isLLBS and sess_uuid:
            try:
                threading.Thread(target=lambda: session.post(f'https://{hostname}/verify', json={'session': sess_uuid}, timeout=10, headers={"Referer":url}), daemon=True).start()
            except:
                pass
                
        mess_session = str(random.randint(100000000000000000, 999999999999999999))
        
        botd_payload = botd_create_frfr_frfr_frfr(sess_uuid)
        
        # chatcumgpt lin
        import urllib.parse as u
        
        Pb = u.parse_qs(u.urlparse(url).query).get("puid",[None])[0]
        iP = bool(Pb)
        
        TCData = {
            "tid": int(tid), "bl": [10], "session": mess_session, "max_tasks": 1,
            "design_id": 139, "cur_url": str(url), "doc_ref": "", "num_of_tasks": "",
            "is_loot": isLLBS, "rkey": key, "cookie_id": str(random.randint(100000000, 999999999)),
            "botd": botd_payload, "botds": sess_uuid, "offer": "0", "tier_id": 4,
            "taboola_user_sync": "", "fid": -1, "clid": str(uuid.uuid4()),
            
            # New XXXTra shit
            
            "additional_info":{},"allow_unlocker":True,"desktop_design":0,"show_unlocker":True,"test_unlocker_app":-1, "unlocker_only":0 
        }
        if iP:
            print(Pb,iP)
            TCData["puid"]=iP # postback handling
            
        print("MCB")
        
        rawr = session.post(f'https://{SYNCER}/tc', json=TCData, cookies={"ci":str(random.randint(1000000000000000,9999999999999999))})
        debug.info(f'TC Status: {rawr.status_code}')
        
        if rawr.status_code == 428:
            debug.warn('/TC Returned 428, bypass patched?')
            # 428 = Invalid data / BotD, shit is patched
            return 'bypass fail! 428'
            
        if rawr.status_code == 200:
            debug.success('/TC Connected!')
            try:
                TCP = rawr.json()
                debug.info(f"TC Response received")
                if isinstance(TCP, list):
                    if not TCP:
                        return 'bypass fail! Empty TC response'
                    TCP = TCP[0]
                    
                task_id = TCP.get('task_id', 0)
                
                # New Task_Clicked event
                requests.get(f"https://enaightdecipie.com/?event=task_clicked&session_id=${task_id}&info=1");
                # End new event shi, it was THAT easy y'all lazy niggas
                
                
                urid = TCP.get('urid')
                TLeft = TCP.get('auto_complete_seconds')
                APUrl = TCP.get('action_pixel_url', '')
                PUURL = TCP.get('postback_url',False)
                if PUURL:
                    print(PUURL)
                    
                if not urid:
                    return 'bypass fail! No urid in TC response'
                    
                daserver = params.get('websocket_domain')
                if not daserver:
                    return 'bypass fail! No websocket_domain'
                result = canserbero(session, daserver, SYNCER, urid, key, tid, mess_session, isLLBS_str, task_id, TLeft, APUrl)
                if result:
                    debug.custom('AdMaven', f'Bypassed successfully', 'MAGENTA', '🈺')
                    return result
                else:
                    return 'bypass fail! Canserbero returned no valid info'
            except Exception as e:
                debug.error(f'/TC parse error: {traceback.format_exc()}')
                return f'bypass fail! TC parse error: {e}'
        else:
            debug.warn(f'/TC returned {rawr.status_code}')
            return f'bypass fail! TC status {rawr.status_code}'
    except Exception as e:
        debug.error(f'OG_getDest error: {traceback.format_exc()}')
        return f'bypass fail! {str(e)}'

def getDest(url):
    res = OG_getDest(url)
    return res

if __name__ == "__main__":
    print(getDest("https://links.lootlabs.gg/s?fJjn&data=ropKerF1C%2BDVFRHtlJ4B3stRPx3lFEDYB2oDjB3ThPSh69WxjLcSsR6Jztj20vw4NG%2F1koL%2BceAV9PuhgrPmCw4NmmUNfZTvbGxEmqSVLmaQy2gtxMklDjREBKKQVZqSXjtqxFNBxtCE0ZtT3%2Foj0vVI3k%2Be3aH90TWWRlCtlW%2BraOY9aws8bcweQELBIdch3o5BxItVuPfFlMPWEVStETRjtkKC%2BD5YuNODaWifsFN4J%2BD4pbFnBnj4s7pZg0NDKCKz9Ifo4dMbAZ2ljkzqIQSbeAZlFG21xW1K8G5K8nOB%2FivvPAV4OEmYOZnbuSgSr6MCGJOENrgBMNPaI8PFPwRGfRNa%2Bp4iFbNj5S%2B6ZX25tXSigT4KhHBq8m7%2F%2FKT89wpwb0jEsyW7ssny4YGZXaMEizaRIA1xZAGTK%2BAO3WFNa7lkaRSBzS4aPidN4e2h6oC0dr5GRnD0uy7G53bXqsYpDhOuVOVcR684OibTQ9Rl38ePnD5J5xS7cJAvmEQ8oyYFpd1oEmf8EL4YSXWLdHED7zfiBuI9RPwhpJeFxXRZkS75UHjrUI8qPR1f04eeLU0xgrillyDr%2Bm5Id1RLA%2BxYm1zLWKat%2B81WgDBIpKV%2BkMgUTyrYaxKcAuySg7BSzxvtE2SFaeono%2Fr%2FPfVZ1FqpRfKHek3ftYdIUtzyHyPkUMtH5cFyrdEuOmU%2FAd%2BE"))
