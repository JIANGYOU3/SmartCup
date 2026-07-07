"""从 Chrome 浏览器导出 secsdk 密钥（websign_env.json）"""
import json, sys, os

def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cdp2 import CDP, get_ws

    # get_ws() 自动在 localhost:9222 找 douyin 页面
    ws = get_ws()
    if not ws:
        print("❌ 未找到 douyin.com 页面！")
        print("   请确保 Chrome 中打开了 www.douyin.com 并已登录")
        sys.exit(1)

    print("✅ 已连接到 douyin.com 页面")

    cdp = CDP(ws)
    cdp.cmd("Runtime.enable")

    # 注入 JS 导出 secsdk 环境
    dump_js = r"""(function(){
      var ls = {};
      for (var i=0;i<localStorage.length;i++){
        var k=localStorage.key(i); ls[k]=localStorage.getItem(k);
      }
      var out = {
        localStorage: ls,
        cookie: document.cookie,
        href: location.href,
        ua: navigator.userAgent,
        ssr_user_id: (window.SSR_RENDER_DATA && window.SSR_RENDER_DATA.app && window.SSR_RENDER_DATA.app.odin) ? window.SSR_RENDER_DATA.app.odin.user_id : null,
        web_secsdk_uid: localStorage.getItem('web_runtime_security_uid')
      };
      return JSON.stringify(out);
    })()"""

    result = cdp.cmd("Runtime.evaluate", {
        "expression": dump_js,
        "returnByValue": True,
        "awaitPromise": True
    })

    res = result.get("result", {})
    if "exceptionDetails" in res:
        print(f"❌ JS 执行异常: {res['exceptionDetails']}")
        sys.exit(1)

    value = res.get("result", {}).get("value", "")
    if not value:
        print("❌ 获取数据为空，请确保在 douyin.com 页面运行此脚本")
        sys.exit(1)

    # 解析
    env = json.loads(value) if isinstance(value, str) else value

    # 保存到项目
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    output_path = os.path.join(
        project_root, 'source', 'douyin_crawler', 'lib', 'reverse', 'websign_env.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(env, f, ensure_ascii=False, indent=2)

    print(f"✅ websign_env.json 已保存!")
    print(f"   输出: {output_path}")
    print(f"   localStorage keys ({len(env.get('localStorage', {}))}):")
    for k in env.get('localStorage', {}):
        print(f"     - {k}")
    print(f"   cookie 长度: {len(env.get('cookie', ''))}")
    print(f"   ssr_user_id: {env.get('ssr_user_id', 'N/A')}")
    cdp.close()

if __name__ == "__main__":
    main()
