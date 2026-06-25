# 知乎数据采集 & AI 标签分类 — 完整工作流教程

> 适用人群：代码小白，想用 AI + 爬虫批量处理数据  
> 最终成果：从知乎链接列表 → 自动爬取完整内容 → AI 打标签 → Excel 汇总表

---

## 目录

1. [项目背景：我们要做什么](#1-项目背景我们要做什么)
2. [准备工作：环境搭建](#2-准备工作环境搭建)
3. [第一步：理解你的原始数据](#3-第一步理解你的原始数据)
4. [第二步：用 AI 给帖子打标签](#4-第二步用-ai-给帖子打标签)
5. [第三步：爬取帖子完整内容](#5-第三步爬取帖子完整内容)
6. [第四步：整理输出 & 转 Excel](#6-第四步整理输出--转-excel)
7. [调试过程：我们踩过的坑](#7-调试过程我们踩过的坑)
8. [完整文件结构](#8-完整文件结构)
9. [常用命令速查](#9-常用命令速查)
10. [如何分享给同门](#10-如何分享给同门)

---

## 1. 项目背景：我们要做什么

### 场景

你在做**高端智能水杯**市场分析，从知乎上找到了 650 条相关帖子。但问题是：

- 你手上只有**标题 + 链接 + 正文开头一小段**，没有完整内容
- 你不知道每条帖子具体在讨论什么品牌、什么产品类型
- 你想按照「标签 + 完整内容 + 点赞评论」来做数据分析

### 目标

```
原始数据（650条链接 + 标题片段）
        │
        ▼
  ① AI 批量打标签（品牌/产品类型/证据理由）
        │
        ▼
  ② 爬虫爬取完整内容（12个字段）
        │
        ▼
  ③ 合并输出 → CSV + Excel 表格
```

### 你需要准备的东西

| 物品 | 说明 | 去哪里弄 |
|------|------|----------|
| DeepSeek API Key | AI 打标签用 | [platform.deepseek.com](https://platform.deepseek.com) 注册，充值 10 块够用很久 |
| 知乎 Cookie | 爬虫登录用 | 浏览器登录知乎 → F12 → Application → Cookies → 复制所有 cookie |
| 一台电脑 | Windows/Mac 都可以 | 需要能装 conda |

---

## 2. 准备工作：环境搭建

### 2.1 安装 conda

conda 是一个 Python 环境管理器，让你不污染系统环境。

- **Windows**：下载 [Miniconda](https://docs.conda.io/en/latest/miniconda.html) 安装包，一路下一步
- **Mac**：终端里运行：
  ```bash
  brew install miniconda
  ```
- **Linux/WSL**：
  ```bash
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
  bash Miniconda3-latest-Linux-x86_64.sh
  ```

安装完成后，**关掉终端重新打开**。

### 2.2 创建项目环境

打开终端（Windows 用 Anaconda Prompt），输入：

```bash
# 创建一个叫 SmartCup 的 Python 环境
conda create -n SmartCup python=3.11 -y

# 激活环境
conda activate SmartCup

# 安装必要的库
pip install requests beautifulsoup4 lxml openpyxl tqdm python-dotenv
```

### 2.3 项目文件夹结构

在你的电脑上创建如下文件夹（可以放在任意位置，比如桌面）：

```
SmartCup/
├── .env                  ← 存放 API Key 和 Cookie（机密！不要上传）
├── .gitignore            ← 告诉 Git 哪些文件不提交
├── CLAUDE.md             ← 项目说明书（给 AI 助手看的）
│
├── source/
│   ├── cleandata/        ← 数据清洗 & AI 标签脚本
│   │   ├── batch_labeler.py    ← 【核心】AI 批量打标签
│   │   ├── deepseek_filter.py  ← 旧版筛选脚本（备用）
│   │   └── csv2xlsx.py         ← CSV 转 Excel 工具
│   │
│   └── zhihu_crawler/    ← 知乎爬虫
│       ├── main.py             ← 爬虫入口
│       ├── config.py           ← 配置文件
│       ├── items.py            ← 数据模型
│       ├── pipelines.py        ← 输出管道
│       ├── middleware.py       ← 中间件
│       ├── utils.py            ← 工具函数
│       └── spiders/
│           └── zhihu.py        ← 【核心】知乎爬虫
│
└── res/data/zhihu/
    ├── raw/               ← 放原始 CSV 数据
    │   └── 标题筛选版1.0.csv
    └── output/            ← 输出结果
        ├── 标签结果.csv
        ├── 标签结果.xlsx
        ├── 爬取结果.csv
        └── 爬取结果.xlsx
```

### 2.4 配置 .env 文件

创建 `.env` 文件（注意：文件名就是 `.env`，没有后缀），内容：

```
# DeepSeek API Key
DEEPSEEK_API_KEY=sk-你的key粘贴在这里

# 知乎 Cookie（浏览器登录知乎后，F12→Application→Cookies→全选复制）
ZHIHU_COOKIE=你的cookie粘贴在这里
```

**⚠️ 重要：这个文件绝对不能上传到 GitHub 或发给别人！** 里面是你的密钥。

---

## 3. 第一步：理解你的原始数据

### 3.1 原始 CSV 长什么样

你手上的 `标题筛选版1.0.csv` 是一个有 12 列的表格：

| 列名 | 实际含义 | 示例 |
|------|----------|------|
| 图片 | 封面图链接 | `https://pica.zhimg.com/...` |
| 内容 | **知乎链接** | `https://www.zhihu.com/question/65459802/answer/1825933343` |
| highlight | **标题** | `有什么好看却又不烂大街的水杯？` |
| highlight1 | 简短标签 | `水杯` |
| richtext | **正文开头** | `家居许美人：冬天倒入开水可以当暖手宝用...` |
| button | **点赞数** | `赞同 4266` |
| 内容6 | **评论数** | `154 条评论` |
| 时间 | 发布时间 | `2022-05-31` |

### 3.2 链接类型分布

650 条链接分成了 4 种类型：

| 类型 | 数量 | URL 特征 | 说明 |
|------|------|----------|------|
| **问答帖** | 340 | `/question/xxx/answer/xxx` | 用户对某个问题的回答 |
| **专栏文章** | 257 | `/p/xxx` | 知乎专栏的长文章 |
| **视频** | 45 | `/zvideo/xxx` | 视频帖子（无文字内容） |
| **问题** | 8 | `/question/xxx`（无 answer） | 纯问题，没有具体回答 |

### 3.3 为什么要区分类型

不同类型的帖子，分析角度不同：

- **问答帖**：能看到答主、赞同数、评论数，适合做口碑分析
- **专栏文章**：长文深度内容，适合做竞品研究
- **视频**：没有文字，爬虫会跳过

---

## 4. 第二步：用 AI 给帖子打标签

### 4.1 为什么要用 AI 打标签

650 条帖子，人工看一遍要几天。用 AI（DeepSeek API）批量处理，几分钟搞定。

AI 做的事情：读标题+正文 → 判断帖子在讨论什么品牌/产品 → 输出标签 + 证据。

### 4.2 AI 输出的格式

每条帖子，AI 只返回一个 JSON（不是大段文字）：

```json
{
  "labels": ["膳魔师", "象印", "虎牌", "品牌对比/横评"],
  "evidence": {
    "膳魔师": "文中提到膳魔师保温杯",
    "象印": "文中对比了象印",
    "虎牌": "文中评测了虎牌",
    "品牌对比/横评": "帖子标题为'日本保温杯三大品牌对比'"
  }
}
```

这样保证输出干净，不会有多余废话，方便程序自动处理。

### 4.3 AI 使用的标签体系（21个）

```
智能水杯/温控杯      电热水杯/加热杯      Ember温控杯
其他国际智能品牌      麦开/Moikit          米家/小米水杯
华为/鸿蒙水杯        哈尔斯               苏泊尔
富光                 希诺                 物生物
膳魔师               象印                 虎牌
Stanley              YETI                 品牌对比/横评
保温杯推荐/导购      其他杯具相关          不相关
```

### 4.4 运行命令

```bash
# 切换到项目目录
cd SmartCup

# 先试跑（不调 API，只检查数据和污染检测）
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --dry-run

# 正式运行（8 个并发，断点续跑）
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --workers 8 --resume
```

### 4.5 脚本做了什么

1. **解析 CSV**：处理跨行的复杂格式，还原成 650 条记录
2. **污染过滤**：自动检测并跳过色情/无关内容（如"飞机杯"、"世界杯"），不发 API
3. **并发调用 DeepSeek**：同时发 8 条请求，节省时间
4. **进度保存**：每 20 条自动保存，中断后 `--resume` 继续
5. **输出 CSV**：原始字段 + AI 标签 + AI 证据理由

### 4.6 输出结果

`标签结果.csv` 包含 8 列：

```
链接 | 标签 | 标题 | 正文开头 | 点赞数 | 评论数 | AI证据理由 | AI原始JSON
```

---

## 5. 第三步：爬取帖子完整内容

### 5.1 为什么要另外爬内容

原始 CSV 里只有正文**开头一小段**（通常不到 100 字）。要分析用户具体说了什么，必须爬完整内容。

### 5.2 爬虫是怎么工作的

```
知乎链接
  │
  ├─ 问答帖 (/question/xxx/answer/xxx)
  │     → 下载页面 HTML
  │     → 提取隐藏的 JSON 数据（js-initialData）
  │     → 从中抽取：回答内容 + 问题信息 + 作者 + 统计
  │
  ├─ 专栏文章 (/p/xxx)
  │     → 同样下载 HTML → 提取 JSON
  │     → 抽取：文章内容 + 作者 + 统计
  │
  ├─ 问题 (/question/xxx)
  │     → 抽取问题信息（无回答内容）
  │
  └─ 视频 (/zvideo/xxx)
        → 跳过（无文字）
```

**关键点**：爬虫不调用知乎 API（容易触发反爬），而是下载普通网页，从网页内嵌的 JSON 数据中提取信息。这种方法更稳定。

### 5.3 爬虫输出的 13 个字段

| 字段 | 含义 | 来源 |
|------|------|------|
| 关键词 | 知乎话题标签 | 网页 JSON |
| **帖子类型** | 问答帖/专栏文章/问题帖/视频 | URL 自动识别 |
| 问题被浏览次数 | 该问题被看了多少次 | 网页 JSON |
| 问题回答个数 | 该问题有多少个回答 | 网页 JSON |
| 问题评论个数 | 问题本身的评论数 | 网页 JSON |
| 问题标题 | 问题/文章标题 | 网页 JSON |
| 问题内容 | 问题的详细描述 | 网页 JSON |
| 答主昵称 | 回答/文章作者 | 网页 JSON |
| 回答时间 | 发布时间 | 网页 JSON |
| 赞同数 | 点赞数 | 网页 JSON |
| 评论数 | 评论数 | 网页 JSON |
| 回答内容 | **完整正文** | 网页 JSON |
| 问答链接 | 原始 URL | 输入 |

### 5.4 运行命令

```bash
# 确保 .env 里填好了 ZHIHU_COOKIE

# 运行爬虫（-u 确保进度条正常显示）
conda run -n SmartCup python -u -m source.zhihu_crawler.main

# 跑完后自动生成 Excel
```

### 5.5 爬虫的安全机制

- **限速**：每条间隔 2 秒 + 随机延迟，不触发知乎反爬
- **断点续爬**：中断后重新运行，自动跳过已处理的链接
- **错误处理**：404/403/超时 都有日志，不影响后续
- **进度条**：实时显示速度、剩余时间、成功/失败计数

---

## 6. 第四步：整理输出 & 转 Excel

### 6.1 最终文件

| 文件 | 内容 |
|------|------|
| `标签结果.csv` | 原始数据 + AI 标签 + 证据 |
| `标签结果.xlsx` | 同上，Excel 格式（蓝底表头、可筛选、链接可点击） |
| `爬取结果.csv` | 完整爬取内容（13 个字段） |
| `爬取结果.xlsx` | 同上，Excel 格式 |

### 6.2 手动 CSV 转 Excel

```bash
conda run -n SmartCup python source/cleandata/csv2xlsx.py res/data/zhihu/output/爬取结果.csv
```

Excel 文件特性：
- 蓝色表头 + 白色粗体
- 首行冻结（滚动时表头始终可见）
- 自动筛选器
- 链接列可点击跳转
- 列宽自动适配内容

---

## 7. 调试过程：我们踩过的坑

这一节记录实际开发中遇到的问题和解决方法，供之后类似项目参考。

### 坑 1：CSV 解析乱掉

**现象**：原始 CSV 中，有些单元格内容包含换行符，导致一条记录被拆成多行。

**解决**：写专门的解析逻辑——遇到以 `http` 开头的链接才算新记录，否则拼接到上一条。

### 坑 2：污染数据误判

**现象**：
- "出差党带恒温杯上飞机" → 被当成 NSFW（关键词"飞机"匹配到了"飞机杯"）
- "象印保温杯 SM-SA48" → 被当成 NSFW（"SM"匹配到了色情内容）
- "如何看待Stanley保温杯走红" → 被当成不相关（"季后赛"匹配到了体育）

**解决**：缩小关键词范围。"飞机杯"保留但去掉"飞机"；"SM"移除（太容易误伤产品型号）；"季后赛"移除（跟杯子话题可能同时出现）。

### 坑 3：API 返回空字段

**现象**：调用知乎 API `/api/v4/answers/xxx` 能拿到数据，但 `content`（正文）、`comment_count`（评论数）、`visit_count`（浏览量）全是空的。

**原因**：知乎 v4 API 默认只返回少量字段，需要加 `include` 参数明确指定要哪些字段。而且问题级别的统计字段（浏览量、回答数）在回答 API 中根本不返回。

**解决**：放弃 API，改用 HTML 解析方案——下载完整网页 → 提取 `<script id="js-initialData">` 中的 JSON → 从 `entities.answers` 和 `entities.questions` 中拿数据。一次请求拿到全部字段。

### 坑 4：请求头触发反爬

**现象**：同样的 Cookie，直接 `requests.get()` 能拿到数据，但用 `requests.Session` 封装后拿到的是空白页面。

**定位**：对比请求头，发现 `Session` 多加了 `Accept-Encoding: gzip, deflate, br` 等头。

**解决**：删掉所有多余的请求头，只保留 `User-Agent` 和 `Cookie`。知乎对请求头很敏感。

### 坑 5：进度条不显示

**现象**：程序在跑，但 tqdm 进度条不出来，只能看到逐条日志。

**原因**：`conda run` 默认缓冲 Python 的标准输出（stdout），导致动态刷新的进度条无法渲染。

**解决**：
1. 运行命令加 `-u` 参数：`python -u` = 禁用输出缓冲
2. 进度条输出到 stderr 而非 stdout（stderr 默认不缓冲）
3. 所有 `print()` 加 `flush=True`

### 坑 6：知乎同一文章有多个 ID

**现象**：两条不同链接 `zhuanlan.zhihu.com/p/30607479585` 和 `zhuanlan.zhihu.com/p/9882026291` 爬到的内容完全一样。

**原因**：这不是爬虫 bug，是作者本人在知乎用两个不同 ID 发了同一篇文章。知乎不检查重复内容。

**处理**：这是数据层面的问题，后续分析时按链接去重即可，不需要改爬虫。

---

## 8. 完整文件结构

```
SmartCup/
│
├── .env                          ← API Key + Cookie（机密，不提交）
├── .env.example                  ← 模板（给同门看的）
├── .gitignore                    ← Git 忽略规则
├── CLAUDE.md                     ← 项目说明书（给 AI 助手读的）
├── README.md                     ← 项目说明（给人读的）
├── environment.yml               ← conda 环境配置
│
├── source/
│   ├── cleandata/                ← 数据清洗模块
│   │   ├── batch_labeler.py      ← 【主脚本】AI 批量标签分类
│   │   ├── deepseek_filter.py    ← 旧版筛选脚本
│   │   └── csv2xlsx.py           ← CSV → Excel 转换
│   │
│   └── zhihu_crawler/            ← 知乎爬虫模块
│       ├── __init__.py
│       ├── main.py               ← 爬虫入口
│       ├── config.py             ← 配置文件
│       ├── items.py              ← 数据模型
│       ├── pipelines.py          ← 输出管道
│       ├── middleware.py         ← 请求中间件
│       ├── utils.py              ← 工具函数
│       └── spiders/
│           ├── __init__.py
│           └── zhihu.py          ← 【核心】爬虫逻辑
│
└── res/
    └── data/
        └── zhihu/
            ├── raw/              ← 原始输入数据
            │   └── 标题筛选版1.0.csv
            └── output/           ← 处理结果
                ├── 标签结果.csv
                ├── 标签结果.xlsx
                ├── 爬取结果.csv
                └── 爬取结果.xlsx
```

---

## 9. 常用命令速查

```bash
# ========== 环境相关 ==========
conda activate SmartCup                                    # 激活环境
conda run -n SmartCup python -u <脚本> [参数]               # 运行脚本（推荐方式）


# ========== AI 打标签 ==========
# 试跑（检查数据和污染）
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --dry-run

# 正式运行（8 并发 + 断点续跑）
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --workers 8 --resume


# ========== 知乎爬虫 ==========
# 爬取完整内容
conda run -n SmartCup python -u -m source.zhihu_crawler.main

# 从头爬取（忽略已有进度）
conda run -n SmartCup python -u -m source.zhihu_crawler.main --no-resume


# ========== 格式转换 ==========
# CSV → 格式化 Excel
conda run -n SmartCup python source/cleandata/csv2xlsx.py res/data/zhihu/output/爬取结果.csv
```

---

## 10. 如何分享给同门

### 10.1 同门需要的文件

把整个项目文件夹发给他（除了 `.env` 和 `res/data/`）。或者上传到 GitHub 后让他 clone。

### 10.2 同门需要做的

```bash
# 1. 安装 conda（同上）

# 2. 用 environment.yml 一键创建环境
conda env create -f environment.yml

# 3. 创建自己的 .env 文件
cp .env.example .env
# 然后编辑 .env，填入他自己的 DeepSeek Key 和知乎 Cookie

# 4. 放入自己的 CSV 数据到 res/data/zhihu/raw/

# 5. 运行！
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --workers 8 --resume
conda run -n SmartCup python -u -m source.zhihu_crawler.main
```

### 10.3 如果有懂代码的朋友帮忙

在项目目录下创建 `CLAUDE.md`，内容是项目说明书（当前已有的那个文件）。这样使用 Claude Code 时，AI 助手会自动了解项目结构和命令，朋友帮忙改代码会更高效。

---

## 附录：关键概念解释

| 概念 | 通俗解释 |
|------|----------|
| **conda** | Python 的"沙盒"，每个项目一个独立环境，不会互相干扰 |
| **API** | 程序之间的接口。DeepSeek API = 把文字发给 DeepSeek，它返回分析结果 |
| **Cookie** | 浏览器的"身份证"，登录知乎后浏览器携带这个来证明你是你 |
| **JSON** | 一种结构化的数据格式，程序好解析，人也能读 |
| **CSV** | 纯文本表格，用逗号分隔列 |
| **并发** | 同时做多件事。`--workers 8` = 同时发 8 条请求 |
| **断点续跑** | 中断后继续从上次停止的地方开始，不重复处理 |
| **反爬** | 网站检测并阻止爬虫的手段。限速 + 伪装成浏览器可以绕过 |
| **HTML** | 网页的源代码。爬虫下载 HTML，从中提取需要的信息 |
| **tqdm** | 进度条库，终端里显示"████░░░░ 45%"那种效果 |
