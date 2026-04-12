# LootLabs Bypass — Open Source

Automatically resolves LootLabs / Loot-Link key system URLs and returns the destination link.  
No browser required. Fully scriptable.

> **Project by MCB Projects** · [Discord](https://trw.lat/ds) · [rip.linkvertise.lol](https://rip.linkvertise.lol)

---

## Features

- Bypasses LootLabs & Loot-Link key systems programmatically
- WebSocket-based task resolution (`canserbero` engine)
- BotD spoofing with AES-GCM encrypted payload
- Cloudflare session handling (via optional `NBA` module)
- Multi-server fallback with automatic retry logic
- Proxy support (HTTP/HTTPS)

---

## Requirements

- Python 3.8+
- Install dependencies:

```bash
pip install requests websocket-client beautifulsoup4 cryptography brotli
```

> The `NBA` module (`CF_Boom`, `debug`) is **not public**. The script falls back to `requests.Session()` automatically if it's not present.

---

## Usage

```python
from bypass import getDest

result = getDest("https://loot-link.com/s?...")
print(result)  # Returns destination URL or error message
```

### Running directly

```bash
python bypass.py
```

Edit the test URL at the bottom of the file.

---

## Return Values

| Result | Meaning |
|---|---|
| A URL string | Bypass successful |
| `bypass fail! ...` | Bypass failed — see reason |

---

## Notes

- Works best with a browser-like session (CF_Boom). Plain `requests.Session()` may fail on Cloudflare-protected links.
- Proxy support is built-in — pass a proxy to `CF_Boom.getSession()`.
- 428 response from `/tc` = BotD check failed / bypass patched.

---

## License

Open source. Do whatever, just don't be lame about it.
