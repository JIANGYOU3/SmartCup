# -*- coding: utf-8 -*-
"""通过 CDP 连接已开调试端口的 Edge(9222)，在抖音页面执行 JS。
用于 hook/断点 拿 a_bogus 算法中间值。
"""
import json
import urllib.request
import websocket  # websocket-client


def get_douyin_page_ws():
    """找到抖音主页面的 webSocketDebuggerUrl"""
    data = json.load(urllib.request.urlopen("http://localhost:9222/json/list"))
    for t in data:
        if t.get("type") == "page" and "douyin.com" in t.get("url", ""):
            return t["webSocketDebuggerUrl"], t.get("url")
    return None, None


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, max_size=None, timeout=30)
        self._id = 0

    def send(self, method, params=None):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        # 读到匹配 id 的响应（跳过事件通知）
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                return msg
            # 否则是事件，忽略

    def eval(self, expr, await_promise=True, timeout_ms=15000):
        r = self.send("Runtime.evaluate", {
            "expression": expr,
            "awaitPromise": await_promise,
            "returnByValue": True,
            "timeout": timeout_ms,
        })
        res = r.get("result", {})
        if "exceptionDetails" in res:
            return {"__error__": res["exceptionDetails"]}
        return res.get("result", {}).get("value")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


if __name__ == "__main__":
    ws_url, url = get_douyin_page_ws()
    print("page url:", url)
    print("ws:", ws_url)
    cdp = CDP(ws_url)
    cdp.send("Runtime.enable")
    # 验证 SDK 就绪
    out = cdp.eval("""(function(){
        return {
            href: location.href.slice(0,40),
            hasSDK: !!(window.byted_acrawler && window.byted_acrawler.frontierSign),
            hasVM: typeof window._$webrt_1668687510
        };
    })()""")
    print("check:", json.dumps(out, ensure_ascii=False))
    cdp.close()
