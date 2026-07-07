/**
 * 动态插桩 bdms.js - 追踪数组写入
 *
 * 策略：用 Node.js Proxy 包装可能的数组对象
 */

const fs = require('fs');
const path = require('path');

// 加载 bdms 环境
require('./env.js');

// Hook 数组写入
let arrayWrites = [];

// Hook Array.prototype 方法
const originalSet = Object.getOwnPropertyDescriptor(Array.prototype, 'length').set;

// 在加载 bdms.js 之前插桩
console.log('准备插桩 bdms.js...');

// 加载 bdms
const bdms = require('./bdms.js');

// Hook String.fromCharCode 捕获最终输出
let final_bb = null;
const oldFromCharCode = String.fromCharCode;
String.fromCharCode = function(...args) {
    if (args.length >= 130 && args.length <= 150) {
        final_bb = args;
        console.log(`捕获 bb: ${args.length} 字节`);
    }
    return oldFromCharCode.apply(String, args);
};

// 生成测试
const url = 'https://www.douyin.com/aweme/v1/web/aweme/detail/?q=1&_t=1700000000000';

Date.now = () => 1700000000000;

const xhr = new XMLHttpRequest();
xhr.bdmsInvokeList = [
    {args: ['GET', url, true], func: function(){}},
    {args: ['Accept', 'application/json'], func: function(){}},
];
xhr.send(null);

const a_bogus = window.a_bogus;

console.log(`\n结果:`);
console.log(`  a_bogus: ${a_bogus.slice(0, 60)}...`);
console.log(`  长度: ${a_bogus.length}`);

if (final_bb) {
    console.log(`  bb 长度: ${final_bb.length}`);

    // 保存结果用于分析
    fs.writeFileSync(
        path.join(__dirname, '../../reverse/dynamic_trace.json'),
        JSON.stringify({
            timestamp: 1700000000000,
            bb: final_bb,
            a_bogus: a_bogus,
            writes: arrayWrites.slice(0, 100), // 只保存前 100 个
        }, null, 2)
    );

    console.log(`\n已保存到 dynamic_trace.json`);
}

console.log(`\n提示: bdms.js 混淆太重，直接插桩困难`);
console.log(`建议: 使用已有的查表法方案`);
