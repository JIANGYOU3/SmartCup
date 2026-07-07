# -*- coding: utf-8 -*-
"""健壮 CDP Debugger 客户端：用独立线程持续收消息，避免 enable 事件洪流阻塞。
在 VM 原生调用点下条件断点，dump bb 处理时的 n/e/返回。
"""
import json
import urllib.request
import websocket
import threading
import queue
import time


def get_ws():
    d = json.load(urllib.request.urlopen("http://localhost:9222/json/list"))
    for t in d:
        if t.get("type") == "page" and "douyin" in t.get("url", ""):
            return t["webSocketDebuggerUrl"]
    return None


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, max_size=None, timeout=60)
        self._id = 0
        self.resp = {}          # id -> result
        self.events = queue.Queue()
        self._stop = False
        self._t = threading.Thread(target=self._reader, daemon=True)
        self._t.start()

    def _reader(self):
        while not self._stop:
            try:
                msg = json.loads(self.ws.recv())
            except Exception:
                break
            if "id" in msg:
                self.resp[msg["id"]] = msg
            elif "method" in msg:
                self.events.put(msg)

    def cmd(self, method, params=None, timeout=20):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        end = time.time() + timeout
        while time.time() < end:
            if mid in self.resp:
                return self.resp.pop(mid)
            time.sleep(0.01)
        return {"__timeout__": True}

    def wait_event(self, method, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            try:
                ev = self.events.get(timeout=0.2)
            except queue.Empty:
                continue
            if ev.get("method") == method:
                return ev
        return None

    def close(self):
        self._stop = True
        try:
            self.ws.close()
        except Exception:
            pass


if __name__ == "__main__":
    cdp = CDP(get_ws())
    print("enable Runtime/Debugger...")
    cdp.cmd("Runtime.enable")
    cdp.cmd("Debugger.enable")
    print("ok. 收集 scriptParsed 找 bdms...")
    # 收集 scriptParsed
    sid = None
    end = time.time() + 8
    while time.time() < end and not sid:
        ev = cdp.wait_event("Debugger.scriptParsed", timeout=2)
        if ev and "bdms_1.0.1.19_fix.js" in ev["params"].get("url", ""):
            sid = ev["params"]["scriptId"]
    print("bdms scriptId:", sid)
    cdp.close()
