/**
 * a_bogus 签名命令行入口（供 Python 子进程调用）
 *
 * 用法：
 *   node sign_cli.js '<json>'
 * 其中 json 形如：
 *   {"url": "https://www.douyin.com/...?a=1", "uifid": "...", "method": "GET", "body": ""}
 *
 * 也可从 stdin 读取同样的 JSON（argv 为空时）。
 * 输出（stdout 最后一行）：
 *   {"a_bogus": "...", "ok": true}
 * 出错：
 *   {"a_bogus": "", "ok": false, "error": "..."}
 *
 * 设计要点：使用持久脚本 + JSON 入参，避免 Python 端用 node -e 拼接代码时的转义问题。
 */
const path = require('path');
const { get_a_bogus } = require(path.join(__dirname, 'bdms/index.js'));

function readInput() {
    // 优先用命令行参数；否则读 stdin
    const arg = process.argv[2];
    if (arg) {
        return Promise.resolve(arg);
    }
    return new Promise((resolve) => {
        let data = '';
        process.stdin.setEncoding('utf8');
        process.stdin.on('data', (chunk) => { data += chunk; });
        process.stdin.on('end', () => resolve(data));
    });
}

(async function main() {
    let out = { a_bogus: '', ok: false };
    try {
        const raw = (await readInput() || '').trim();
        const params = raw ? JSON.parse(raw) : {};
        const url = params.url || '';
        const uifid = params.uifid || '';
        const method = params.method || 'GET';
        const body = params.body || '';
        const a_bogus = get_a_bogus(url, uifid, method, body);
        out = { a_bogus: a_bogus || '', ok: !!a_bogus };
    } catch (e) {
        out = { a_bogus: '', ok: false, error: String(e && e.stack || e) };
    }
    // 恢复 process（env.js 中曾删除），保证输出正常
    if (global._process) global.process = global._process;
    // 用明确前缀输出，方便 Python 端在混杂日志中定位结果
    process.stdout.write('\n__SIGN_RESULT__' + JSON.stringify(out) + '\n');
    process.exit(0);
})();
