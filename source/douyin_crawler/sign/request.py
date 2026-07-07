# -*- encoding: utf-8 -*-
'''
@File    :   request.py
@Time    :   2024年07月15日
@Author  :   erma0
@Version :   1.1
@Link    :   参考   https://github.com/ShilongLee/Crawler/blob/main/service/douyin/logic/common.py
@Desc    :   抖音sign
'''
import json
import os
import random
import re
import subprocess
from urllib.parse import quote

import httpx

from .cookies import get_cookie_dict

# execjs 为可选依赖，仅在使用 JS 签名回退时才需要
try:
    from utils.execjs_fix import execjs  # type: ignore
    _HAS_EXECJS = True
except ImportError:
    execjs = None  # type: ignore
    _HAS_EXECJS = False

# loguru 回退到 logging
try:
    from loguru import logger  # type: ignore
except ImportError:
    import logging
    logger = logging.getLogger(__name__)  # type: ignore


class Request(object):
    HOST = 'https://www.douyin.com'
    LIVE_HOST = 'https://live.douyin.com'
    WEB2_HOST = 'https://www-hj.douyin.com'
    PARAMS = {
        'device_platform': 'webapp',
        'aid': '6383',
        'channel': 'channel_pc_web',
        'update_version_code': '170400',
        'pc_client_type': '1',  # Windows
        'version_code': '190500',
        'version_name': '19.5.0',
        'cookie_enabled': 'true',
        'screen_width': '2560',  # from cookie dy_swidth
        'screen_height': '1440',  # from cookie dy_sheight
        'browser_language': 'zh-CN',
        'browser_platform': 'Win32',
        'browser_name': 'Chrome',
        'browser_version': '126.0.0.0',
        'browser_online': 'true',
        'engine_name': 'Blink',
        'engine_version': '126.0.0.0',
        'os_name': 'Windows',
        'os_version': '10',
        'cpu_core_num': '24',  # device_web_cpu_core
        'device_memory': '8',  # device_web_memory_size
        'platform': 'PC',
        'downlink': '10',
        'effective_type': '4g',
        'round_trip_time': '50',
        # 'webid': '',   # from doc
        # 'verifyFp': '',   # from cookie s_v_web_id
        # 'fp': '', # from cookie s_v_web_id
        # 'msToken': '',  # from cookie msToken
        # 'a_bogus': '' # sign
    }
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "sec-ch-ua-platform": "Windows",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        "referer": "https://www.douyin.com/?recommend=1",
        "priority": "u=1, i",
        "pragma": "no-cache",
        "cache-control": "no-cache",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "accept": "application/json, text/plain, */*",
        "dnt": "1",
    }
    WEBSIGN_URIS = [
        '/aweme/v1/web/tab/feed/',
        '/aweme/v1/web/aweme/favorite/',
        '/aweme/v2/web/module/feed/',
        '/aweme/v1/web/follow/feed/',
        '/aweme/v1/web/general/search/single/',
        '/aweme/v1/web/search/item/',
    ]
    SIGN = None  # 延迟编译，仅 JS 回退路径需要
    WEBID = ''
    client = httpx.Client(
        timeout=30.0,
        verify=False,
        follow_redirects=True
    )

    def __init__(self, cookie='', UA=''):
        self.filepath = os.path.dirname(os.path.abspath(__file__))
        self.COOKIES = get_cookie_dict(cookie)
        if UA:  # 如果需要访问搜索页面源码等内容，需要提供cookie对应的UA
            version = UA.split(' Chrome/')[1].split(' ')[0]
            _version = version.split('.')[0]
            self.HEADERS.update({
                "User-Agent": UA,  # 主要是这个
                "sec-ch-ua": f'"Chromium";v="{_version}", "Not(A:Brand";v="24", "Google Chrome";v="{_version}"',
            })
            self.PARAMS.update({
                "browser_version": version,
                "engine_version": version,  # 主要是这个
            })

    def get_sign(self, uri: str, params: dict) -> dict:
        query = '&'.join([f'{k}={quote(str(v))}' for k, v in params.items()])
        call_name = 'sign_datail'
        if 'reply' in uri:
            call_name = 'sign_reply'
        a_bogus = self.SIGN.call(
            call_name, query, self.HEADERS.get("User-Agent"))
        return a_bogus

    def get_sign_bdms(self, full_url: str, params: dict, method: str = 'GET', body: str = '') -> str:
        """使用 bdms 方案生成 a_bogus 签名（通过 Node.js 子进程）

        Args:
            full_url: 完整的请求 URL（含域名，如 https://www.douyin.com/aweme/v1/...）
            params: 请求参数字典（会拼到 URL query 上参与签名）
            method: 请求方法，GET / POST，需与实际请求一致
            body: POST 请求体（application/x-www-form-urlencoded 字符串），参与签名
        """
        query = '&'.join([f'{k}={quote(str(v))}' for k, v in params.items()])
        # full_url 已经包含完整域名，直接拼接参数
        url = f'{full_url}?{query}'
        uifid = self.COOKIES.get('UIFID', '')

        # 使用持久的 CLI 脚本 + JSON(stdin) 入参，避免 node -e 拼接代码的转义问题
        # 用绝对路径，保证 Node 的 __dirname / require 解析正确
        js_path = os.path.abspath(
            os.path.join(self.filepath, '..', 'lib', 'runtime', 'sign_cli.js'))
        js_dir = os.path.dirname(js_path)
        payload = json.dumps({
            'url': url,
            'uifid': uifid,
            'method': (method or 'GET').upper(),
            'body': body or '',
        })
        try:
            result = subprocess.run(
                ['node', js_path],
                input=payload,
                capture_output=True,
                text=True,
                timeout=40,
                cwd=js_dir,
            )
            # 结果以 __SIGN_RESULT__ 前缀输出，便于在混杂日志中定位
            marker = '__SIGN_RESULT__'
            for line in result.stdout.splitlines():
                idx = line.find(marker)
                if idx != -1:
                    data = json.loads(line[idx + len(marker):])
                    a_bogus = data.get('a_bogus', '')
                    if a_bogus:
                        return a_bogus
                    logger.error(f"bdms 签名为空: {data.get('error', '')}")
                    return ''
            logger.error(
                f"bdms 签名失败 (code={result.returncode})\n"
                f"  stdout: {result.stdout[-500:]}\n"
                f"  stderr: {result.stderr[-500:]}")
        except subprocess.TimeoutExpired:
            logger.error("bdms 签名超时")
        except Exception as e:
            logger.error(f"调用 Node.js 生成签名出错: {e}")
        return ''

    def get_sign_pure(self, full_url: str, params: dict, timestamp: int = None) -> str:
        """纯 Python 生成 a_bogus（查表法）

        Args:
            full_url: 完整的请求 URL
            params: 请求参数字典
            timestamp: 毫秒时间戳（可选，默认当前时间）

        Returns:
            192 长度的 a_bogus 字符串
        """
        try:
            from .abogus_pure import generate_abogus
            import time

            if timestamp is None:
                timestamp = int(time.time() * 1000)

            query = '&'.join([f'{k}={quote(str(v))}' for k, v in params.items()])
            url = f'{full_url}?{query}'

            return generate_abogus(url, timestamp)
        except Exception as e:
            logger.error(f"纯 Python 生成 a_bogus 失败: {e}")
            return ''

    def get_websign(self, full_url: str, params: dict) -> dict:
        """使用 secsdk 补环境生成 x-secsdk-web-signature（通过 Node.js 子进程）

        返回 {'uifid':..., 'timestamp':..., 'signature':...}；失败返回 {}。
        注意：调用前 params 里应已包含 a_bogus（浏览器实际签名顺序：先 a_bogus 后 secsdk）。

        Args:
            full_url: 完整请求 URL（含域名）
            params: 请求参数字典（拼到 URL query 上参与 secsdk 签名）
        """
        query = '&'.join([f'{k}={quote(str(v))}' for k, v in params.items()])
        url = f'{full_url}?{query}'

        js_path = os.path.abspath(
            os.path.join(self.filepath, '..', 'lib', 'runtime', 'sign_websign.js'))
        js_dir = os.path.dirname(js_path)
        payload = json.dumps({'url': url})
        try:
            result = subprocess.run(
                ['node', js_path],
                input=payload,
                capture_output=True,
                text=True,
                timeout=40,
                cwd=js_dir,
            )
            marker = '__WEBSIGN_RESULT__'
            for line in result.stdout.splitlines():
                idx = line.find(marker)
                if idx != -1:
                    data = json.loads(line[idx + len(marker):])
                    if data.get('ok'):
                        return {
                            'uifid': data.get('uifid', ''),
                            'timestamp': data.get('timestamp', ''),
                            'signature': data.get('signature', ''),
                        }
                    logger.error(f"secsdk 签名失败: {data.get('error', '')}")
                    return {}
            logger.error(
                f"secsdk 签名失败 (code={result.returncode})\n"
                f"  stdout: {result.stdout[-500:]}\n"
                f"  stderr: {result.stderr[-500:]}")
        except subprocess.TimeoutExpired:
            logger.error("secsdk 签名超时")
        except Exception as e:
            logger.error(f"调用 Node.js 生成 secsdk 签名出错: {e}")
        return {}

    def get_params(self, params: dict) -> dict:
        params.update(self.PARAMS)
        params['msToken'] = self.get_ms_token()
        params['screen_width'] = self.COOKIES.get('dy_swidth', 2560)
        params['screen_height'] = self.COOKIES.get('dy_sheight', 1440)
        params['cpu_core_num'] = self.COOKIES.get('device_web_cpu_core', 24)
        params['device_memory'] = self.COOKIES.get('device_web_memory_size', 8)
        params['verifyFp'] = self.COOKIES.get('s_v_web_id', None)
        params['fp'] = self.COOKIES.get('s_v_web_id', None)
        params['uifid'] = self.COOKIES.get('UIFID', None)
        params['webid'] = self.get_webid()
        return params

    def get_webid(self):
        if not self.WEBID:
            url = 'https://www.douyin.com/?recommend=1'
            text = self.getHTML(url)
            pattern = r'\\"user_unique_id\\":\\"(\d+)\\"'
            match = re.search(pattern, text)
            if match:
                self.WEBID = match.group(1)
        return self.WEBID

    def get_ms_token(self, randomlength=120):
        """
        返回cookie中的msToken或随机字符串
        """
        ms_token = self.COOKIES.get('msToken', None)
        if not ms_token:
            ms_token = ''
            base_str = 'ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789='
            length = len(base_str) - 1
            for _ in range(randomlength):
                ms_token += base_str[random.randint(0, length)]
        return ms_token

    def getHTML(self, url) -> str:
        headers = self.HEADERS.copy()
        headers['sec-fetch-dest'] = 'document'
        response = self.client.get(url, headers=headers, cookies=self.COOKIES)
        if response.status_code != 200 or response.text == '':
            logger.error(f'HTML请求失败, url: {url}, header: {headers}')
            return ''
        return response.text

    def getJSON(self, uri: str, params: dict, data: dict = None, live=None, web2=None):
        url = f'{self.HOST}{uri}'
        live_url = f'{self.LIVE_HOST}{uri}'
        web2_url = f'{self.WEB2_HOST}{uri}'
        params = self.get_params(params)

        # 确定签名 URL（根据 live/web2 参数）
        if web2:
            sign_url = web2_url
        elif live:
            sign_url = live_url
        else:
            sign_url = url

        # 需要 POST 的接口列表（提前定义，签名时需要知道方法）
        post_uris = ['/aweme/v2/web/module/feed/', '/aweme/v1/web/commit/item/digg/']

        # 特定接口使用 bdms 签名（其余仍走旧的纯算法 get_sign）
        # 注意：签名 URL 必须与实际请求 URL（含域名）完全一致
        bdms_uris = ['/aweme/v1/web/tab/feed/', '/aweme/v2/web/module/feed/',
                     '/aweme/v1/web/locate/post/', '/aweme/v1/web/commit/item/digg/',
                     '/aweme/v1/web/aweme/favorite/', '/aweme/v1/web/follow/feed/',
                     '/aweme/v1/web/general/search/single/',
                     '/aweme/v1/web/search/item/']
        if uri in bdms_uris:
            sign_method = 'POST' if uri in post_uris else 'GET'
            sign_body = ''
            if data is not None:
                sign_body = '&'.join(
                    [f'{k}={quote(str(v))}' for k, v in data.items()])
            # 浏览器实际签名顺序：先 a_bogus（URL 不含 secsdk 三参数），
            # 再由 secsdk 末尾追加 uifid + timestamp + x-secsdk-web-signature。
            if uri in self.WEBSIGN_URIS:
                # secsdk 会在末尾追加 uifid，base 参数里不应预置（否则顺序/值不一致）
                params.pop('uifid', None)

            # 使用纯 Python 生成 a_bogus（查表法）
            params["a_bogus"] = self.get_sign_pure(sign_url, params)

            # 需要 secsdk 三件套签名的接口（feed/favorite 等会校验 web-signature）
            if uri in self.WEBSIGN_URIS:
                ws = self.get_websign(sign_url, params)
                if ws:
                    params["uifid"] = ws["uifid"]
                    params["timestamp"] = ws["timestamp"]
                    params["x-secsdk-web-signature"] = ws["signature"]
        else:
            # 其他接口使用纯 Python 生成 a_bogus
            params["a_bogus"] = self.get_sign_pure(url, params)

        # 这个接口必须更改referer的值为当前请求页面的url
        referer_map = {
            '/aweme/v1/web/aweme/related/': f"https://www.douyin.com/video/{params.get('aweme_id')}",
            '/aweme/v1/web/comment/list/': f"https://www.douyin.com/video/{params.get('aweme_id')}",
            '/aweme/v1/web/comment/list/reply/': f"https://www.douyin.com/video/{params.get('item_id')}",
            '/aweme/v1/web/user/profile/other/': f"https://www.douyin.com/user/{params.get('sec_user_id')}?",
            '/aweme/v1/web/aweme/post/': f"https://www.douyin.com/user/{params.get('sec_user_id')}?",
            '/aweme/v1/web/locate/post/': f"https://www.douyin.com/",
            '/aweme/v1/web/im/spotlight/relation/': f"https://www.douyin.com/user/",
            '/aweme/v1/web/user/following/list/': f"https://www.douyin.com/user/",
            '/aweme/v1/web/user/follower/list/': f"https://www.douyin.com/user/",
            '/aweme/v1/web/aweme/favorite/': f"https://www.douyin.com/",
            '/aweme/v1/web/aweme/listcollection/': f"https://www.douyin.com/user/self?from_tab_name=main&showTab=favorite_collection",
            '/aweme/v1/web/music/listcollection/': f"https://www.douyin.com/user/self?from_tab_name=main&showSubTab=music&showTab=favorite_collection",
            '/aweme/v1/web/collects/video/list/': f"https://www.douyin.com/user/self?from_tab_name=main&showSubTab=favorite_folder&showTab=favorite_collection",
            '/aweme/v1/web/collects/list/': f"https://www.douyin.com/user/self?from_tab_name=main&showSubTab=favorite_folder&showTab=favorite_collection",
            '/aweme/v1/web/mix/listcollection/': f"https://www.douyin.com/user/self?from_tab_name=main&showSubTab=favorite_folder&showTab=favorite_collection",
            '/aweme/v1/web/series/collections': f"https://www.douyin.com/user/self?from_tab_name=main&showSubTab=favorite_folder&showTab=favorite_collection",
            '/aweme/v1/web/mix/list/': f"https://www.douyin.com/user/",
            '/aweme/v1/web/home/search/item/': f"https://www.douyin.com/user/",
            '/aweme/v1/web/seo/inner/link/': f"https://www.douyin.com/user/",
            '/aweme/v2/web/module/feed/': f"https://www.douyin.com/jingxuan",
            '/aweme/v1/web/general/search/single/': f"https://www.douyin.com/search/{params.get('keyword', '')}?type=general",
            '/aweme/v1/web/search/item/': f"https://www.douyin.com/search/{params.get('keyword', '')}?type=general",
            '/aweme/v1/web/tab/feed/': f"https://www.douyin.com/?recommend=1",
        }
        for pattern, referer_value in referer_map.items():
            if pattern == uri:
                self.HEADERS['referer'] = referer_value
                break

        # www-hj.douyin.com 需要 bd-ticket-guard headers（favorite 等接口）
        if sign_url.startswith('https://www-hj.douyin.com'):
            self.HEADERS['origin'] = 'https://www.douyin.com'
            bd_client_data_v2 = self.COOKIES.get("bd_ticket_guard_client_data_v2", "")
            if bd_client_data_v2:
                self.HEADERS["bd-ticket-guard-client-data"] = bd_client_data_v2
                # 从 v2 里解码 ree_public_key（标准 base64，不是 URL-safe）
                try:
                    import base64
                    # 修复 padding
                    missing = len(bd_client_data_v2) % 4
                    if missing:
                        bd_client_data_v2 += '=' * (4 - missing)
                    decoded = json.loads(base64.b64decode(bd_client_data_v2).decode('utf-8'))
                    ree_key = decoded.get('ree_public_key', '')
                    if ree_key:
                        self.HEADERS["bd-ticket-guard-ree-public-key"] = ree_key
                except Exception:
                    pass
            self.HEADERS["bd-ticket-guard-version"] = "2"
            self.HEADERS["bd-ticket-guard-web-version"] = "2"
            self.HEADERS["bd-ticket-guard-web-sign-type"] = "1"
            # uifid 既要在 query 也要在 header
            if params.get("uifid"):
                self.HEADERS["uifid"] = params["uifid"]

        if data is not None or uri in post_uris:
            bd_client_data = self.COOKIES.get("bd_ticket_guard_client_data", None)
            self.HEADERS["Content-Type"] = "application/x-www-form-urlencoded"
            self.HEADERS["Uifid"] = self.COOKIES.get("UIFID", None)
            # self.HEADERS["Bd-Ticket-Guard-Client-Data"] = bd_client_data
            # self.HEADERS["Bd-Ticket-Guard-Web-Version"] = '1'
            # self.HEADERS["Bd-Ticket-Guard-Version"] = '2'
            # self.HEADERS["Bd-Ticket-Guard-Iteration-Version"] = '1'
            self.HEADERS["X-Secsdk-Csrf-Token"] = 'DOWNGRADE'
            # POST 请求时也要判断是否使用 web2
            if web2:
                post_headers = self.HEADERS.copy()
                post_headers['sec-fetch-site'] = 'same-site'
                post_headers['origin'] = 'https://www.douyin.com'
                response = self.client.post(
                    web2_url, params=params, data=data or {}, headers=post_headers, cookies=self.COOKIES)
                actual_url = web2_url
            else:
                response = self.client.post(
                    url, params=params, data=data or {}, headers=self.HEADERS, cookies=self.COOKIES)
                actual_url = url
            print(f'POST url:{response.url}, code:{response.status_code}')
        elif live:
            response = self.client.get(
                live_url, params=params, headers=self.HEADERS, cookies=self.COOKIES)
            print(f'url:{response.url}, code:{response.status_code}')
            actual_url = live_url
        elif web2:
            # web2 请求需要修改 headers（跨子域名）
            web2_headers = self.HEADERS.copy()
            web2_headers['sec-fetch-site'] = 'same-site'
            # origin 已在前面 bd-ticket-guard 逻辑里设置
            response = self.client.get(
                web2_url, params=params, headers=web2_headers, cookies=self.COOKIES)
            print(f'url:{response.url}, code:{response.status_code}')
            actual_url = web2_url
        else:
            response = self.client.get(
                url, params=params, headers=self.HEADERS, cookies=self.COOKIES)
            # print(f'url:{response.url}, header:{self.HEADERS}')
            actual_url = url
        # 尝试解析 JSON 响应
        try:
            json_data = response.json() if response.text else {}
        except Exception:
            json_data = {'error': 'Invalid JSON response', 'raw': response.text[:500] if response.text else ''}

        if response.status_code != 200:
            logger.error(
                f'JSON请求失败：url: {actual_url}, params: {params}, header: {self.HEADERS}, code: {response.status_code}, body: {response.text[:500] if response.text else "empty"}')

        # 返回元组：(数据, HTTP状态码)，让调用方可以直接使用
        return json_data, response.status_code


if __name__ == "__main__":
    r = Request()
    print(r.get_webid())
