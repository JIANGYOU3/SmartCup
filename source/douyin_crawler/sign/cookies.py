import os

import httpx

try:
    import ujson as json
except ImportError:
    import json  # type: ignore

try:
    from loguru import logger  # type: ignore
except ImportError:
    import logging
    logger = logging.getLogger(__name__)  # type: ignore

try:
    import browser_cookie3  # type: ignore
except ImportError:
    browser_cookie3 = None  # type: ignore

from .util import save_json


def get_cookie_dict(cookie='') -> dict:
    if cookie:
        # 自动读取的cookie有效期短，且不一定有效
        if cookie in ['edge', 'chrome']:
            cj = eval(f"browser_cookie3.{cookie}(domain_name='douyin.com')")
            cookie = dict(httpx.Cookies(cj))
        else:
            cookie = normalize_cookie(cookie)
        save_cookie(cookie)
    elif os.path.exists('config/cookie.json'):
        with open('config/cookie.json', 'r', encoding='utf-8') as f:
            cookie = normalize_cookie(f.read())
        # 读到的若是损坏的旧格式，修复后回写一次
        save_cookie(cookie)
    elif os.path.exists('config/cookie.txt'):
        with open('config/cookie.txt', 'r', encoding='utf-8') as f:
            cookie = normalize_cookie(f.read())
        save_cookie(cookie)
    else:
        cookie = normalize_cookie(input('请输入cookie:'))
        save_cookie(cookie)
    return cookie


def normalize_cookie(cookie) -> dict:
    """把任意形态的 cookie 输入统一成扁平 {name: value} 字典。

    支持：
      - 已是 dict（直接用）
      - JSON 字符串 {"k":"v",...}
      - 浏览器 cookie 字符串 "k=v; k2=v2"
      - 被多层 JSON 序列化损坏的内容（历史 bug 产物），自动逐层解开
    """
    obj = cookie
    # 最多解 10 层，防御历史上的多重 JSON.stringify 嵌套
    for _ in range(10):
        if isinstance(obj, dict):
            # 已是扁平 cookie 字典
            if 'sessionid' in obj or 'ttwid' in obj or _looks_flat(obj):
                obj.pop('', None)
                return obj
            keys = list(obj.keys())
            # 损坏形态：{ "<整段JSON字符串>": "<尾巴>" }
            if len(keys) <= 2 and isinstance(keys[0], str) and keys[0].lstrip().startswith('{'):
                cand, tail = keys[0], obj[keys[0]]
                for attempt in (cand, cand + '"' + str(tail) + '"}', cand + str(tail)):
                    try:
                        obj = json.loads(attempt)
                        break
                    except ValueError:
                        continue
                else:
                    obj.pop('', None)
                    return obj
                continue
            obj.pop('', None)
            return obj
        if isinstance(obj, str):
            s = obj.strip()
            # 优先按 JSON 解析（兼容被多次 stringify 成 "\"{...}\"" 的字符串）
            if s.startswith('{') or s.startswith('"'):
                try:
                    obj = json.loads(s)
                    continue
                except ValueError:
                    pass
            # 否则按浏览器 cookie 字符串解析
            return cookies_str_to_dict(s)
        # 其它类型，尽力转 dict
        try:
            return dict(obj)
        except Exception:
            return {}
    # 兜底
    return obj if isinstance(obj, dict) else {}


def _looks_flat(d: dict) -> bool:
    """判断字典是否像扁平 cookie（key 短、无 JSON 串当 key）。"""
    if not d:
        return False
    for k in d.keys():
        if not isinstance(k, str) or len(k) > 120 or k.lstrip().startswith('{'):
            return False
    return True


def save_cookie(cookie: dict):
    # 始终保存扁平字典，避免重复 JSON 包裹
    if not isinstance(cookie, dict):
        cookie = normalize_cookie(cookie)
    save_json('config/cookie', cookie)


def test_cookie(cookie):
    url = 'https://sso.douyin.com/check_login/'
    if type(cookie) is dict:
        cookie_dict = cookie
    elif type(cookie) is str:
        cookie_dict = cookies_str_to_dict(cookie)

    res = httpx.get(url, cookies=cookie_dict).json()
    if res['has_login'] is True:
        logger.success('cookie已登录')
        return True
    else:
        logger.error('cookie未登录')
        return False


def cookies_str_to_dict(cookie_string: str) -> dict:
    cookies = cookie_string.strip().split('; ')
    cookie_dict = {}
    for cookie in cookies:
        if cookie == '' or cookie == 'douyin.com' or '=' not in cookie:
            continue
        key, value = cookie.split('=', 1)
        key = key.strip()
        if key:
            cookie_dict[key] = value
    return cookie_dict


def cookies_dict_to_str(cookie_string: dict) -> str:
    return '; '.join([f'{key}={value}' for key, value in cookie_string.items()])


if __name__ == "__main__":
    save_json('edge_cookie', get_cookie_dict())
    # save_json('dict_cookie', cookies_to_dict(x))
