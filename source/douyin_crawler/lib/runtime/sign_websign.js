/**
 * x-secsdk-web-signature 命令行入口（供 Python 子进程调用）
 *
 * 用法：node sign_websign.js '<json>'   或   stdin 传 JSON
 *   {"url": "https://www-hj.douyin.com/...?a=1"}
 * 输出（stdout 最后一行）：
 *   __WEBSIGN_RESULT__{"signed_url":"...","uifid":"...","timestamp":"...","signature":"...","ok":true}
 *
 * signed_url 是带 uifid + timestamp + x-secsdk-web-signature 的完整 URL，
 * Python 端可直接从中取出这三个参数附加到请求上。
 */
const path = require('path');
// 先存住 process（websign_env.js 加载时会 delete global.process）
const _process = process;
const ws = require(path.join(__dirname, 'secsdk/websign_index.js'));
// 恢复 process，供下面输出使用
if (typeof process === 'undefined' && global._process) global.process = global._process;
if (typeof global.process === 'undefined') global.process = _process;

function readInput() {
    const arg = process.argv[2];
    if (arg) return Promise.resolve(arg);
    return new Promise((resolve) => {
        let data = '';
        process.stdin.setEncoding('utf8');
        process.stdin.on('data', (c) => { data += c; });
        process.stdin.on('end', () => resolve(data));
    });
}

function parseParam(u, key) {
    const m = String(u).match(new RegExp('[?&]' + key.replace(/[-]/g, '\\$&') + '=([^&]+)'));
    return m ? m[1] : '';
}

(async function main() {
    let out = { ok: false };
    try {
        const raw = (await readInput() || '').trim();
        const params = raw ? JSON.parse(raw) : {};
        const url = params.url || '';
        const signed = ws.web_sign(url);
        out = {
            signed_url: signed,
            uifid: parseParam(signed, 'uifid'),
            timestamp: parseParam(signed, 'timestamp'),
            signature: parseParam(signed, 'x-secsdk-web-signature'),
            ok: !!parseParam(signed, 'x-secsdk-web-signature'),
        };
    } catch (e) {
        out = { ok: false, error: String(e && e.stack || e) };
    }
    process.stdout.write('\n__WEBSIGN_RESULT__' + JSON.stringify(out) + '\n');
    process.exit(0);
})();
