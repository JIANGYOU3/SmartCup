/**
 * 抖音签名生成入口（bdms.js 补环境方案 - 研究中）
 *
 * ============================================================
 * bdms.js 补环境研究笔记
 * ============================================================
 *
 *
 * 【问题分析】
 * 1. bdms.js 只是初始化模块，提供 window.bdms.init() 和 getReferer()
 * 2. bdms.js 中的 fetch wrapper（3750行）只处理请求体 Content-Type，不涉及签名
 * 3. 真正的签名逻辑在 JSVMP bytecode 中，但需要正确触发
 *
 *
 * 【继续研究方向】
 * 1. 从抖音网页获取 webmssdk.js 文件
 * 2. 分析 webmssdk.js 如何调用 bdms 生成签名
 * 3. 参考开源项目：
 *    - https://github.com/HZhertz/ByteDance-a_bogus-parameter
 *    - https://github.com/naiveliberty/Douyin_Spider
 *
 * 【关键代码位置】
 * - bdms.js:6336-6370 - JSVMP 虚拟机入口函数 J()
 * - bdms.js:6372-6456 - JSVMP 执行函数 X()，包含函数调用拦截
 * - bdms.js:7699-7827 - JSVMP 初始化调用和 window.bdms 导出
 * - bdms.js:3750-3752 - fetch wrapper（只处理请求体）
 *
 * 【环境补全要点】
 * - env.js 已实现基本浏览器环境模拟
 * - 需要触发鼠标事件（addEventListener + dispatchEvent）
 * - 需要正确的 URLSearchParams.size 检测绕过
 * - 隐藏 Node.js process 对象（bdms.js:564 检测）
 *
 * ============================================================
 */

// 默认 User-Agent
const defaultUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

// 获取当前文件所在目录
const path = require('path');
const libDir = path.dirname(__filename);

// 加载环境模块
const envUtils = require(path.join(libDir, 'env'));

// 加载 bdms 模块
require(path.join(libDir, 'bdms'));

// bdms 加载完成后立即恢复 process，供 execjs 输出结果
if (envUtils && envUtils.restoreProcess) {
    envUtils.restoreProcess();
}

// 关键：bdms.js 加载后会替换 URLSearchParams，需要重新 hook
// 钩住新的 URLSearchParams.prototype.set 来捕获 a_bogus
const originalSet = URLSearchParams.prototype.set;
URLSearchParams.prototype.set = function(key, value) {
    if (key === 'a_bogus') {
        window.a_bogus = value;
    }
    return originalSet.call(this, key, value);
};

// 初始化 bdms
if (window.bdms && window.bdms.init) {
    window.bdms.init({ aid: 6383 });
}

// 模拟鼠标轨迹（bdms 需要鼠标轨迹数据才能生成有效签名）
// 在初始化时生成一段模拟轨迹
if (envUtils && envUtils.simulateMouseTrack) {
    envUtils.simulateMouseTrack({
        points: 25,
        startX: 100,
        startY: 200,
        endX: 800,
        endY: 500,
        duration: 600
    });
}

/**
 * 生成 a_bogus 签名（当前不可用，需要配合 webmssdk.js）
 *
 * @param {string} urlParams - URL 参数字符串
 * @param {string} userAgent - User-Agent 字符串 (可选)
 * @returns {string} a_bogus 签名值
 */
function sign(urlParams, userAgent) {
    userAgent = userAgent || defaultUserAgent;

    // 重置 a_bogus
    window.a_bogus = null;

    // 更新 User-Agent
    window.navigator.userAgent = userAgent;

    // 构造完整 URL
    const fullUrl = 'https://www.douyin.com/aweme/v1/web/aweme/detail/?' + urlParams;

    // 完整的请求头
    const headers = {
        'User-Agent': userAgent,
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        'referer': 'https://www.douyin.com/?recommend=1',
        'priority': 'u=1, i',
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'accept': 'application/json, text/plain, */*',
        'dnt': '1'
    };

    // 使用 fetch 发起请求触发 bdms 签名（当前不工作，需要 webmssdk.js）
    // fetch(fullUrl, {
    //     method: 'GET',
    //     headers: headers,
    //     credentials: 'include',
    //     mode: 'cors'
    // });


    // 获取 a_bogus
    // const aBogus = windows.a_bogus;

    if (!aBogus) {
        throw new Error('签名生成失败：未能获取 a_bogus（需要配合 webmssdk.js 使用）');
    }

    return aBogus;
}

function get_a_bogus(url, uifid, method, body){
    // 每次生成签名前模拟一段新的鼠标轨迹
    if (envUtils && envUtils.simulateMouseTrack) {
        envUtils.simulateMouseTrack({
            points: Math.floor(Math.random() * 10) + 15,  // 15-25 个点
            duration: Math.floor(Math.random() * 300) + 400  // 400-700ms
        });
    }

    // 重置上一次的签名结果，避免误用旧值
    window.a_bogus = null;

    // 默认 GET；点赞等接口为 POST
    method = (method || 'GET').toUpperCase();
    var accept = 'application/json,text/plain,*/*';

    try {
        var xhr = new XMLHttpRequest();
        // bdmsInvokeList 模拟 XHR 调用顺序：open(method,url,async) -> setRequestHeader -> ...
        var invokeList = [
            {"args": [method, url, true], func:function (){}},
            {"args": ["Accept", accept], func:function (){}},
            {"args":["uifid", uifid || ""]}
        ];
        // POST 请求需要声明请求体的 Content-Type，bdms 会把请求体纳入签名
        if (method !== 'GET' && method !== 'HEAD') {
            invokeList.splice(2, 0, {
                "args": ["Content-Type", "application/x-www-form-urlencoded"],
                func: function (){}
            });
        }
        xhr.bdmsInvokeList = invokeList;
        // GET/HEAD 无请求体；其它方法传入 body（字符串）
        xhr.send((method === 'GET' || method === 'HEAD') ? null : (body || null));
    } catch(e) {
        // 忽略 VM 执行错误
    }
    return window.a_bogus
}

// 导出接口
module.exports = {
    sign: sign,
    get_a_bogus: get_a_bogus,
    defaultUserAgent: defaultUserAgent,
    envUtils: envUtils  // 导出 envUtils 供外部调用
};

// 直接运行测试
if (require.main === module) {
    const params = 'aid=6383&device_platform=webapp&version_code=170400&version_name=17.4.0';
    const userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
    try {
        // const result = sign(params, userAgent);
        const a_bogus = get_a_bogus('https://www.douyin.com/aweme/v1/web/aweme/detail/?' + params);

        console.log('a_bogus:', a_bogus);
    } catch (e) {
        console.log('Error:', e.message);
    }
    // 恢复 process 并退出
    if (global._process) {
        global.process = global._process;
    }
    process.exit(0);
}
