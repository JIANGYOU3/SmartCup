// -*- coding: utf-8 -*-
/**
 * 采集多个不同时间的 VM trace
 *
 * 修改 bdms 环境，记录 VM 执行 trace
 */

const fs = require('fs');
const path = require('path');

// 加载 bdms 环境
require('./env.js');

const bdms = require('./bdms.js');

// Hook String.fromCharCode 捕获输出
let captured_bb = null;
const original_fromCharCode = String.fromCharCode;
String.fromCharCode = function(...args) {
    if (args.length >= 130 && args.length <= 145) {
        captured_bb = args;
    }
    return original_fromCharCode.apply(String, args);
};

// Hook VM 执行（尝试记录指令）
// 策略：在 bdms.js 执行前后插入日志
const vm_trace = [];
let trace_enabled = false;

// 测试用例
const TEST_CASES = [
    { T: 1700000000000, desc: 'base' },
    { T: 1700000001000, desc: '+1s' },
    { T: 1700000010000, desc: '+10s' },
    { T: 1700000100000, desc: '+100s' },
    { T: 1700001000000, desc: '+1000s' },
];

console.log('=== 采集多个 trace ===\n');

const results = [];

for (const tc of TEST_CASES) {
    const url = `https://www.douyin.com/aweme/v1/web/aweme/detail/?q=1&_t=${tc.T}`;

    // Hook Date.now
    const oldNow = Date.now;
    Date.now = () => tc.T;

    captured_bb = null;

    // 生成 a_bogus
    const xhr = new XMLHttpRequest();
    xhr.bdmsInvokeList = [
        {args: ['GET', url, true], func: function(){}},
        {args: ['Accept', 'application/json'], func: function(){}},
    ];
    xhr.send(null);

    const a_bogus = window.a_bogus;

    Date.now = oldNow;

    if (captured_bb) {
        results.push({
            T: tc.T,
            desc: tc.desc,
            bb: captured_bb,
            a_bogus: a_bogus,
        });
        console.log(`[${tc.desc}] T=${tc.T}, bb_len=${captured_bb.length}, a_bogus_len=${a_bogus.length}`);
    }
}

// 保存结果
const outFile = path.join(__dirname, '../../reverse/multi_traces.json');
fs.writeFileSync(outFile, JSON.stringify(results, null, 2));

console.log(`\n已保存 ${results.length} 个 trace 到: multi_traces.json`);
console.log('\n下一步：差分分析找出时间相关字节的变化规律');
