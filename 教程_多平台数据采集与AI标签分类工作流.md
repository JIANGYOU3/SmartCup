# 多平台数据采集 & AI 标签分类 — 完整工作流教程

> 适用人群：代码小白，想用 AI + 爬虫批量处理多平台数据  
> 支持平台：知乎 · 抖音 · （淘宝 / 小红书 / B站 可扩展）  
> 最终成果：关键词搜索 → 自动爬取完整内容 → AI 打标签 → Excel 汇总表

---

## 目录

1. [项目全景：一个框架，多平台复用](#1-项目全景一个框架多平台复用)
2. [准备工作：环境搭建](#2-准备工作环境搭建)
3. [通用工作流：四步走](#3-通用工作流四步走)
4. [平台指南 A：知乎](#4-平台指南-a知乎)
5. [平台指南 B：抖音](#5-平台指南-b抖音)
6. [跨平台模块：AI 批量打标签](#6-跨平台模块ai-批量打标签)
7. [整理输出 & 转 Excel](#7-整理输出--转-excel)
8. [如何添加新平台（淘宝/小红书/B站...）](#8-如何添加新平台淘宝小红书b站)
9. [调试过程：我们踩过的坑](#9-调试过程我们踩过的坑)
10. [完整文件结构](#10-完整文件结构)
11. [常用命令速查](#11-常用命令速查)
12. [如何分享给同门](#12-如何分享给同门)

---

## 1. 项目全景：一个框架，多平台复用

### 核心理念

不管爬知乎、抖音还是淘宝，数据处理的逻辑是一样的：

```
关键词搜索 ──→ 爬取内容 ──→ 数据清洗 ──→ AI 打标签 ──→ Excel 输出
   │               │              │              │              │
   │         每个平台有         公共模块         公共模块       公共模块
   │         自己的爬虫         复用            复用           复用
```

**你只需要为新平台写一个爬虫**，清洗、打标签、导出全部复用现有代码。

### 目前已支持的平台

| 平台 | 爬虫模块 | 数据特点 | 反爬难度 |
|------|----------|----------|----------|
| **知乎** | `zhihu_crawler/` | 问答/专栏/视频，长文本为主 | ⭐⭐ 中等 |
| **抖音** | `douyin_crawler/` | 短视频/图文，含评论+互动数据 | ⭐⭐⭐ 较高 |
| **淘宝** | 待开发 | 商品详情+评价 | ⭐⭐⭐⭐ 高 |
| **小红书** | 待开发 | 笔记+评论 | ⭐⭐⭐⭐ 高 |
| **B站** | 待开发 | 视频+弹幕+评论 | ⭐⭐⭐ 较高 |

### 你需要准备的东西

| 物品 | 说明 | 去哪里弄 |
|------|------|----------|
| DeepSeek API Key | AI 打标签用 | [platform.deepseek.com](https://platform.deepseek.com) 注册，充值 10 块够用很久 |
| 平台 Cookie | 爬虫登录用（每个平台各一个） | 浏览器登录目标网站 → F12 → Application → Cookies |
| 一台电脑 | Windows/Mac/Linux 都可以 | 需要能装 conda |

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

### 2.3 配置 .env 文件

创建 `.env` 文件（注意：文件名就是 `.env`，没有后缀），内容：

```
# ========== AI 服务 ==========
DEEPSEEK_API_KEY=sk-你的key粘贴在这里

# ========== 知乎 ==========
ZHIHU_COOKIE=你的知乎cookie粘贴在这里

# ========== 抖音 ==========
DOUYIN_COOKIE=你的抖音cookie粘贴在这里

# ========== 淘宝（预留）==========
# TAOBAO_COOKIE=你的淘宝cookie粘贴在这里
```

**⚠️ 重要：这个文件绝对不能上传到 GitHub 或发给别人！** 里面是你的密钥。

### 2.4 Cookie 怎么获取

每个平台都需要登录后的 Cookie：

1. 用 **Chrome/Edge 浏览器** 登录目标网站
2. 按 `F12` 打开开发者工具
3. 切换到 `Application`（应用程序）标签
4. 左侧找到 `Cookies` → 点击网站域名
5. 全选所有 Cookie，复制为字符串
6. 粘贴到 `.env` 对应的位置

> **抖音特别注意**：抖音 Cookie 有时效性，过期后需要重新获取。如果爬虫返回空白数据，先检查 Cookie 是否过期。

---

## 3. 通用工作流：四步走

不管哪个平台，完整的数据处理流程都是这四步：

### 第一步：获取原始链接（搜索/采集）

从关键词出发，用搜索爬虫批量发现帖子/视频/商品链接。

```bash
# 知乎：关键词搜索 → 发现链接
conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯,恒温杯" --pages 5

# 抖音：关键词搜索 → 发现链接
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯,恒温杯" --pages 5
```

### 第二步：爬取完整内容

用链接列表爬虫，逐条下载完整内容（正文、作者、互动数据等）。

```bash
# 知乎：爬取已有链接的完整内容
conda run -n SmartCup python -u -m source.zhihu_crawler.main

# 抖音：爬取已有链接的视频详情
conda run -n SmartCup python -u -m source.douyin_crawler.main
```

### 第三步：AI 批量打标签

用 DeepSeek API 对爬取结果进行智能分类。

```bash
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --workers 8 --resume
```

### 第四步：输出 Excel

将 CSV 结果转为格式化的 Excel 表格。

```bash
conda run -n SmartCup python source/cleandata/csv2xlsx.py <你的CSV文件路径>
```

### 流程示意图

```
                    ┌─────────────────────────────┐
                    │  关键词搜索 (search_main)      │
                    │  各平台各自实现                  │
                    └─────────────┬───────────────┘
                                  │ 链接列表 CSV
                                  ▼
                    ┌─────────────────────────────┐
                    │  爬取完整内容 (main)            │
                    │  各平台各自实现                  │
                    └─────────────┬───────────────┘
                                  │ 爬取结果 CSV（含完整正文）
                                  ▼
                    ┌─────────────────────────────┐
                    │  AI 批量打标签 (batch_labeler) │
                    │  🔄 跨平台复用                  │
                    └─────────────┬───────────────┘
                                  │ 标签结果 CSV
                                  ▼
                    ┌─────────────────────────────┐
                    │  CSV → Excel (csv2xlsx)       │
                    │  🔄 跨平台复用                  │
                    └─────────────────────────────┘
                                  │ 格式化 Excel
                                  ▼
                             📊 数据分析
```

---

## 4. 平台指南 A：知乎

### 4.1 知乎数据特点

- **内容类型**：问答帖、专栏文章、视频、纯问题
- **链接格式**：
  - 问答帖：`https://www.zhihu.com/question/{qid}/answer/{aid}`
  - 专栏文章：`https://zhuanlan.zhihu.com/p/{post_id}`
  - 视频：`https://www.zhihu.com/zvideo/{id}`
  - 问题：`https://www.zhihu.com/question/{qid}`
- **数据价值**：长文本、深度讨论，适合口碑分析和竞品研究

### 4.2 链接类型分布

| 类型 | URL 特征 | 说明 |
|------|----------|------|
| **问答帖** | `/question/xxx/answer/xxx` | 用户对某个问题的回答，含答主+赞同+评论 |
| **专栏文章** | `/p/xxx` | 知乎专栏的长文章，适合深度研究 |
| **视频** | `/zvideo/xxx` | 视频帖子（无文字内容），爬虫会跳过 |
| **问题** | `/question/xxx`（无 answer） | 纯问题，没有具体回答 |

### 4.3 知乎爬虫是怎么工作的

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

### 4.4 知乎输出字段（13个）

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

### 4.5 知乎爬虫的安全机制

- **限速**：每条间隔 2 秒 + 随机延迟，不触发知乎反爬
- **断点续爬**：中断后重新运行，自动跳过已处理的链接
- **错误处理**：404/403/超时 都有日志，不影响后续
- **进度条**：实时显示速度、剩余时间、成功/失败计数

### 4.6 知乎运行命令

```bash
# 关键词搜索 + 自动爬取
conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯,恒温杯,Ember温控杯,华为水杯" \
  --pages 5

# 仅搜索不爬取（先看结果再决定）
conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯" --pages 3 --search-only

# 基于已有链接列表爬取完整内容
conda run -n SmartCup python -u -m source.zhihu_crawler.main

# 从头爬取（忽略已有进度）
conda run -n SmartCup python -u -m source.zhihu_crawler.main --no-resume
```

---

## 5. 平台指南 B：抖音

### 5.1 抖音数据特点

- **内容类型**：短视频、图文、直播
- **数据价值**：高互动量（点赞/评论/收藏/分享），适合热度分析和用户口碑
- **反爬特点**：抖音反爬比知乎严格得多，需要 **a_bogus 签名** + **Cookie 验证**，并发数降低到 2

### 5.2 抖音爬虫是怎么工作的

```
关键词 → 抖音搜索 API（优先 CDP 浏览器环境；API 方案需要 a_bogus 签名）
  │
  ├─ 搜索阶段
  │     → 调用搜索接口，翻页获取视频列表
  │     → 收集 aweme_id + 链接（自动去重）
  │     → 可选：仅搜索不爬取（--search-only）
  │
  └─ 爬取阶段
        → 访问每个视频的页面 HTML
        → 提取 RENDER_DATA（内嵌的加密 JSON）
        → 解密得到：视频信息 + 作者数据 + 互动统计
        → 可选：抓取评论（--with-comments）
```

**与知乎的关键区别**：
- 知乎是「先有链接列表 → 爬内容」；抖音支持「从关键词出发 → 搜索 → 爬取」一条龙
- 抖音需要 **a_bogus 签名**（一个反爬参数），项目已内置纯 Python 实现，无需额外配置
- 抖音 Cookie 有严格的时效性，过期后爬虫会失败

### 5.3 每次运行前：启动 Chrome 调试模式（必做）

抖音搜索 API 经常触发风控。项目会自动回退到 **CDP 浏览器搜索**：由已登录的 Chrome 发起请求，因此需要先启动一个带调试端口的独立浏览器窗口。

1. 在 Windows PowerShell 运行以下命令（Windows 不支持 `google-chrome` 命令）：

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --remote-allow-origins=* `
  --user-data-dir="$env:TEMP\smartcup-chrome" `
  "https://www.douyin.com"
```

2. 在新打开的 Chrome 中登录抖音，保持 `www.douyin.com` 页面打开。
3. 回到项目终端，执行验证命令；看到 `READY` 后再开始搜索：

```bash
conda run -n SmartCup python -c "from source.douyin_crawler.lib.cdp2 import get_ws; print('READY' if get_ws() else 'NOT_RUNNING')"
```

若 Chrome 在 32 位目录，把 `$env:ProgramFiles` 改为 `${env:ProgramFiles(x86)}`；也可改用 Edge 的 `msedge.exe`。`NOT_RUNNING` 表示端口未启动或当前 WSL/终端无法连接；WebSocket 403 表示启动参数漏了 `--remote-allow-origins=*`。

> 安全提示：上述参数只应用于临时的 `smartcup-chrome` 浏览器目录，不要用于日常 Chrome 配置。

### 5.4 抖音输出字段（14+ 基础字段 + 评论展开列）

**基础字段**：

| 字段 | 含义 |
|------|------|
| 关键词 | 搜索用的关键词 |
| 视频类型 | 短视频 / 图文 / 直播 |
| 播放数 | 视频播放量 |
| 评论数 | 评论总数 |
| 视频标题 | 视频标题/描述 |
| 视频文案 | 完整视频文案 |
| 作者昵称 | 创作者昵称 |
| 作者粉丝量 | 创作者粉丝数 |
| 发布时间 | 视频发布时间 |
| 点赞数 | 点赞数 |
| 收藏数 | 收藏数 |
| 分享数 | 分享数 |
| 视频时长 | 视频时长（秒） |
| 视频链接 | 抖音视频 URL |

**评论字段**（使用 `--with-comments` 时展开，每条评论占 15 列）：
评论N, 评论N点赞, 评论N回复数, 评论N用户, 评论N时间, 评论N属地, 评论N子回复1~3（含用户+点赞）

### 5.5 抖音运行命令

```bash
# 关键词搜索 + 自动爬取（基础版，不抓评论）
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯,恒温杯,Ember温控杯" \
  --pages 5

# 搜索 + 爬取 + 评论（完整版）
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯" \
  --pages 5 \
  --with-comments \
  --comment-pages 5

# 仅搜索不爬取（先看结果再决定）
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯" --pages 3 --search-only

# 按最新发布排序（默认按最多点赞）
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯" --pages 5 --sort 2

# 基于已有链接列表爬取
conda run -n SmartCup python -u -m source.douyin_crawler.main \
  --input res/data/douyin/raw/链接列表.csv \
  --output res/data/douyin/output/爬取结果.csv
```

### 5.6 抖音爬虫注意事项

- **并发限制**：默认只有 2 个并发（`MAX_WORKERS = 2`），不要调高，否则容易触发风控
- **请求间隔**：每条间隔 3 秒 + 随机延迟
- **Cookie 过期**：抖音 Cookie 通常几小时到一天就会过期，爬取失败时优先检查
- **CDP 前置条件**：关键词搜索前先启动调试 Chrome 并确认验证命令输出 `READY`
- **排序方式**：`--sort 0` 综合、`--sort 1` 最多点赞（默认）、`--sort 2` 最新发布

---

## 6. 跨平台模块：AI 批量打标签

这是整个项目最核心的**跨平台复用模块**。不管数据来自知乎还是抖音，打标签的逻辑完全一样。

### 6.1 为什么要用 AI 打标签

几百上千条帖子，人工看一遍要几天。用 AI（DeepSeek API）批量处理，几分钟搞定。

AI 做的事情：读标题+正文 → 判断帖子在讨论什么品牌/产品 → 输出标签 + 证据。

### 6.2 AI 输出的格式

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

### 6.3 AI 使用的标签体系（21个）

```
智能水杯/温控杯      电热水杯/加热杯      Ember温控杯
其他国际智能品牌      麦开/Moikit          米家/小米水杯
华为/鸿蒙水杯        哈尔斯               苏泊尔
富光                 希诺                 物生物
膳魔师               象印                 虎牌
Stanley              YETI                 品牌对比/横评
保温杯推荐/导购      其他杯具相关          不相关
```

> 💡 **标签体系是如何设计的**：覆盖了「智能温控」「国际品牌」「国产品牌」「日本品牌」「北美品牌」「导购推荐」六个维度。你的研究课题不同，标签体系也应该不同——修改 `batch_labeler.py` 中的 `LABELS` 常量即可。

### 6.4 运行命令

```bash
# 先试跑（不调 API，只检查数据和污染检测）
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --dry-run

# 正式运行（8 个并发，断点续跑）
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --workers 8 --resume
```

### 6.5 脚本做了什么

1. **解析 CSV**：处理跨行的复杂格式
2. **污染过滤**：自动检测并跳过色情/无关内容，不发 API（节省费用）
3. **并发调用 DeepSeek**：同时发 8 条请求，节省时间
4. **进度保存**：每 20 条自动保存，中断后 `--resume` 继续
5. **输出 CSV**：原始字段 + AI 标签 + AI 证据理由

### 6.6 输出结果

`标签结果.csv` 包含原始字段 + 以下 AI 列：

```
链接 | 标签 | 标题 | 正文开头 | 点赞数 | 评论数 | AI证据理由 | AI原始JSON
```

---

## 7. 整理输出 & 转 Excel

### 7.1 最终文件

| 文件 | 内容 |
|------|------|
| `标签结果.csv` | 原始数据 + AI 标签 + 证据 |
| `标签结果.xlsx` | 同上，Excel 格式（蓝底表头、可筛选、链接可点击） |
| `爬取结果.csv` | 完整爬取内容 |
| `爬取结果.xlsx` | 同上，Excel 格式 |

### 7.2 手动 CSV 转 Excel

```bash
# 知乎数据
conda run -n SmartCup python source/cleandata/csv2xlsx.py res/data/zhihu/output/爬取结果.csv

# 抖音数据
conda run -n SmartCup python source/cleandata/csv2xlsx.py res/data/douyin/output/爬取结果.csv
```

Excel 文件特性：
- 蓝色表头 + 白色粗体
- 首行冻结（滚动时表头始终可见）
- 自动筛选器
- 链接列可点击跳转
- 列宽自动适配内容

---

## 8. 如何添加新平台（淘宝/小红书/B站...）

项目设计了统一的架构，添加新平台只需 **4 个步骤**。

### 8.1 架构总览

```
source/
├── common/                   ← 🔄 公共模块（所有平台复用）
│   ├── paths.py              ← 路径工具
│   ├── excel_style.py        ← Excel 样式
│   ├── text_utils.py         ← 文本清洗
│   ├── pollution.py          ← 污染检测关键词
│   └── csv_utils.py          ← CSV 解析
│
├── cleandata/                ← 🔄 数据清洗 & AI 标签（所有平台复用）
│   ├── batch_labeler.py      ← AI 批量打标签
│   └── csv2xlsx.py           ← CSV → Excel
│
├── zhihu_crawler/            ← 知乎爬虫
├── douyin_crawler/           ← 抖音爬虫
└── taobao_crawler/           ← 🆕 淘宝爬虫（你要新建的）
```

### 8.2 新建平台的 4 个步骤

以淘宝为例：

#### 步骤 1：创建爬虫目录

```bash
mkdir -p source/taobao_crawler/spiders
touch source/taobao_crawler/__init__.py
touch source/taobao_crawler/spiders/__init__.py
```

#### 步骤 2：编写 5 个标准文件

每个平台爬虫都遵循相同的文件结构：

```
taobao_crawler/
├── __init__.py
├── config.py          ← 配置：Cookie、延迟、并发数
├── items.py           ← 数据模型：定义输出字段
├── pipelines.py       ← 输出管道：CSV / JSON 写入
├── main.py            ← 爬虫入口：基于链接列表爬取
├── search_main.py     ← 搜索入口：基于关键词搜索
└── spiders/
    ├── __init__.py
    └── taobao.py      ← 核心爬虫逻辑
```

**config.py 模板**：

```python
"""淘宝爬虫配置"""
import os
from source.common.paths import get_project_root, get_data_dir, load_env
load_env()

class TaobaoCrawlerConfig:
    PROJECT_ROOT = get_project_root()
    DATA_RAW = get_data_dir("taobao") / "raw"
    DATA_OUTPUT = get_data_dir("taobao") / "output"
    REQUEST_DELAY = 3.0          # 淘宝反爬严格，建议 3-5 秒
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    MAX_WORKERS = 2              # 建议低并发
    COOKIE = os.getenv("TAOBAO_COOKIE", "")
    USER_AGENT = "Mozilla/5.0 ..."
    OUTPUT_ENCODING = "utf-8-sig"

config = TaobaoCrawlerConfig()
```

**items.py 模板**：

```python
"""淘宝数据模型"""
from dataclasses import dataclass, field

@dataclass
class TaobaoItem:
    url: str = ""
    title: str = ""             # 商品标题
    price: str = ""             # 价格
    shop_name: str = ""         # 店铺名
    sales_count: str = ""       # 销量
    # ... 根据实际需要添加字段

    def to_dict(self) -> dict:
        return {
            "关键词": "",
            "商品标题": self.title,
            "价格": self.price,
            "店铺名": self.shop_name,
            "销量": self.sales_count,
            "商品链接": self.url,
        }
```

**pipelines.py 模板**：

```python
"""淘宝爬虫 — 输出管道"""
import csv
from pathlib import Path
from .items import TaobaoItem
from .config import config

class CsvPipeline:
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._writer = None

    def open(self):
        self._file = open(self.output_path, "w", encoding=config.OUTPUT_ENCODING, newline="")
        # 根据 items.py 中的字段名设置 fieldnames
        fieldnames = ["关键词", "商品标题", "价格", "店铺名", "销量", "商品链接"]
        self._writer = csv.DictWriter(self._file, fieldnames=fieldnames)
        self._writer.writeheader()
        self._file.flush()

    def write(self, item: TaobaoItem):
        self._writer.writerow(item.to_dict())
        self._file.flush()

    def close(self):
        if self._file:
            self._file.close()
```

#### 步骤 3：实现核心爬虫逻辑

在 `spiders/taobao.py` 中实现实际的爬取逻辑。核心思路：

1. 用 `requests` 发 HTTP 请求（带 Cookie + User-Agent）
2. 解析返回的 HTML/JSON
3. 提取需要的字段
4. 返回 `TaobaoItem` 对象

```python
"""淘宝核心爬虫"""
import requests
from ..items import TaobaoItem
from ..config import config

def crawl_item(url: str, keyword: str = "") -> TaobaoItem | None:
    """爬取单个淘宝商品"""
    headers = {
        "User-Agent": config.USER_AGENT,
        "Cookie": config.COOKIE,
    }
    try:
        resp = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
        # TODO: 解析 HTML，提取商品信息
        item = TaobaoItem(url=url)
        item.title = "..."  # 从 HTML 提取
        return item
    except Exception as e:
        print(f"爬取失败: {url} - {e}")
        return None
```

#### 步骤 4：注册到公共路径

在 `source/common/paths.py` 中不需要修改——`get_data_dir("taobao")` 已经可以直接使用。

### 8.3 新平台接入检查清单

| 步骤 | 内容 | 完成？ |
|------|------|--------|
| 1 | 创建 `source/{平台名}_crawler/` 目录 | ☐ |
| 2 | 编写 `config.py`（Cookie、延迟、并发） | ☐ |
| 3 | 编写 `items.py`（数据模型、输出字段） | ☐ |
| 4 | 编写 `pipelines.py`（CSV/JSON 输出） | ☐ |
| 5 | 编写 `spiders/{平台名}.py`（核心爬虫） | ☐ |
| 6 | 编写 `main.py`（链接列表入口） | ☐ |
| 7 | 编写 `search_main.py`（关键词搜索入口，可选） | ☐ |
| 8 | `.env` 添加对应平台的 Cookie | ☐ |
| 9 | `res/data/{平台名}/raw/` 和 `output/` 目录 | ☐ |
| 10 | 爬取结果可直接送入 `batch_labeler.py` 打标签 | ☐ |
| 11 | 爬取结果可直接用 `csv2xlsx.py` 转 Excel | ☐ |

### 8.4 设计原则

1. **一个平台 = 一个目录**：所有相关代码放在一起，互不干扰
2. **统一接口**：每个平台的 `Item.to_dict()` 返回字典，`Pipeline` 负责写入
3. **复用公共模块**：路径、样式、文本清洗全部从 `source/common/` 导入
4. **渐进开发**：先做 `main.py`（链接列表爬取），搜索功能（`search_main.py`）可以后加
5. **低并发 + 长延迟**：新平台先保守设置（1-2 并发，3-5 秒延迟），稳定后再优化

---

## 9. 调试过程：我们踩过的坑

这一节记录实际开发中遇到的问题和解决方法，供之后类似项目参考。

### 坑 1：CSV 解析乱掉

**现象**：原始 CSV 中，有些单元格内容包含换行符，导致一条记录被拆成多行。

**解决**：写专门的解析逻辑——遇到以 `http` 开头的链接才算新记录，否则拼接到上一条。

**影响平台**：所有（`source/common/csv_utils.py` 统一处理）

---

### 坑 2：污染数据误判

**现象**：
- "出差党带恒温杯上飞机" → 被当成 NSFW（关键词"飞机"匹配到了"飞机杯"）
- "象印保温杯 SM-SA48" → 被当成 NSFW（"SM"匹配到了色情内容）
- "如何看待Stanley保温杯走红" → 被当成不相关（"季后赛"匹配到了体育）

**解决**：缩小关键词范围。"飞机杯"保留但去掉"飞机"；"SM"移除（太容易误伤产品型号）；"季后赛"移除（跟杯子话题可能同时出现）。

**影响平台**：所有（`source/common/pollution.py` 统一处理）

---

### 坑 3：知乎 API 返回空字段

**现象**：调用知乎 API `/api/v4/answers/xxx` 能拿到数据，但 `content`（正文）、`comment_count`（评论数）、`visit_count`（浏览量）全是空的。

**原因**：知乎 v4 API 默认只返回少量字段，需要加 `include` 参数明确指定要哪些字段。而且问题级别的统计字段（浏览量、回答数）在回答 API 中根本不返回。

**解决**：放弃 API，改用 HTML 解析方案——下载完整网页 → 提取 `<script id="js-initialData">` 中的 JSON → 从 `entities.answers` 和 `entities.questions` 中拿数据。一次请求拿到全部字段。

---

### 坑 4：请求头触发反爬

**现象**：同样的 Cookie，直接 `requests.get()` 能拿到数据，但用 `requests.Session` 封装后拿到的是空白页面。

**定位**：对比请求头，发现 `Session` 多加了 `Accept-Encoding: gzip, deflate, br` 等头。

**解决**：删掉所有多余的请求头，只保留 `User-Agent` 和 `Cookie`。很多平台对请求头很敏感。

**影响平台**：知乎、抖音（通用经验）

---

### 坑 5：进度条不显示

**现象**：程序在跑，但 tqdm 进度条不出来，只能看到逐条日志。

**原因**：`conda run` 默认缓冲 Python 的标准输出（stdout），导致动态刷新的进度条无法渲染。

**解决**：
1. 运行命令加 `-u` 参数：`python -u` = 禁用输出缓冲
2. 进度条输出到 stderr 而非 stdout（stderr 默认不缓冲）
3. 所有 `print()` 加 `flush=True`

**影响平台**：所有

---

### 坑 6：知乎同一文章有多个 ID

**现象**：两条不同链接 `zhuanlan.zhihu.com/p/30607479585` 和 `zhuanlan.zhihu.com/p/9882026291` 爬到的内容完全一样。

**原因**：这不是爬虫 bug，是作者本人在知乎用两个不同 ID 发了同一篇文章。知乎不检查重复内容。

**处理**：这是数据层面的问题，后续分析时按链接去重即可，不需要改爬虫。

---

### 坑 7：抖音 a_bogus 签名 🆕

**现象**：抖音搜索 API 返回空结果或错误。

**原因**：抖音对所有 API 请求都要求携带 `a_bogus` 签名参数，这是抖音的反爬核心机制。没有正确的签名，API 直接拒绝请求。

**解决**：项目已经集成了 `sign/` 模块（fork 自 douyin-api），纯 Python 实现，自动为每个请求添加签名，无需额外配置。Cookie + 签名双重保障。

---

### 坑 8：抖音搜索返回空结果或提示 Chrome/CDP 不可用 🆕

**现象**：搜索 API 返回空结果、提示 `verify_check`，或终端提示找不到 `localhost:9222` / WebSocket 403。

**原因**：抖音搜索被风控后需要 CDP 回退；Chrome 未以调试模式启动、未登录抖音，或缺少 `--remote-allow-origins=*` 参数。

**解决**：按本章“每次运行前：启动 Chrome 调试模式”启动独立 Chrome，登录后在项目终端运行 `get_ws()` 验证命令，确认输出 `READY`。Windows 请使用 `chrome.exe`，不要使用 Linux 的 `google-chrome` 命令。

---

### 坑 9：抖音 Cookie 过期 🆕

**现象**：之前能正常爬取，过几小时后再跑就全部失败。

**原因**：抖音 Cookie 时效性比知乎短得多，通常几个小时就会过期。

**解决**：重新从浏览器复制 Cookie 到 `.env`。建议爬取前先检查 Cookie 是否有效。

---

### 坑 10：抖音 RENDER_DATA 解密 🆕

**现象**：下载了抖音视频页面的 HTML，但数据全部是乱的。

**原因**：抖音把视频数据藏在 `RENDER_DATA` 这个加密字符串里，不是标准的 JSON。

**解决**：`sign/` 模块内置了解密逻辑，自动从 HTML 中提取并解密 RENDER_DATA。

---

## 10. 完整文件结构

```
SmartCup/
│
├── .env                          ← API Key + 各平台 Cookie（机密，不提交）
├── .env.example                  ← 配置模板（给同门看的）
├── .gitignore                    ← Git 忽略规则
├── CLAUDE.md                     ← 项目说明书（给 AI 助手读的）
├── README.md                     ← 项目说明（给人读的）
├── environment.yml               ← conda 环境配置
│
├── source/
│   ├── common/                   ← 🔄 公共模块（所有平台复用）
│   │   ├── paths.py              ← 统一路径获取
│   │   ├── excel_style.py        ← Excel 样式封装
│   │   ├── text_utils.py         ← 文本清洗工具
│   │   ├── pollution.py          ← 污染检测关键词
│   │   └── csv_utils.py          ← 多行 CSV 解析
│   │
│   ├── cleandata/                ← 🔄 数据清洗 & AI 标签（所有平台复用）
│   │   ├── batch_labeler.py      ← 【核心】AI 批量打标签
│   │   ├── deepseek_filter.py    ← 旧版筛选脚本（备用）
│   │   └── csv2xlsx.py           ← CSV → Excel 转换
│   │
│   ├── zhihu_crawler/            ← 知乎爬虫
│   │   ├── main.py               ← 爬虫入口（链接列表）
│   │   ├── search_main.py        ← 搜索入口（关键词）
│   │   ├── config.py             ← 配置
│   │   ├── items.py              ← 数据模型
│   │   ├── pipelines.py          ← 输出管道
│   │   ├── middleware.py         ← 请求中间件
│   │   ├── utils.py              ← 工具函数
│   │   └── spiders/
│   │       ├── zhihu.py          ← 核心爬虫
│   │       └── search.py         ← 搜索爬虫
│   │
│   ├── douyin_crawler/           ← 抖音爬虫
│   │   ├── main.py               ← 爬虫入口（链接列表）
│   │   ├── search_main.py        ← 搜索入口（关键词）
│   │   ├── config.py             ← 配置
│   │   ├── items.py              ← 数据模型（含评论）
│   │   ├── pipelines.py          ← 输出管道
│   │   ├── sign/                 ← a_bogus 签名模块
│   │   │   ├── request.py        ← 自动签名请求
│   │   │   ├── abogus_pure.py    ← 纯 Python a_bogus
│   │   │   ├── cookies.py        ← Cookie 管理
│   │   │   └── data/             ← 签名映射表
│   │   └── spiders/
│   │       ├── douyin.py         ← 核心爬虫（RENDER_DATA）
│   │       └── search.py         ← 搜索爬虫
│   │
│   └── taobao_crawler/           ← 🆕 淘宝爬虫（待开发，参考上面模板）
│
└── res/
    └── data/
        ├── zhihu/
        │   ├── raw/              ← 原始输入数据
        │   └── output/           ← 处理结果
        └── douyin/
            ├── raw/              ← 原始输入数据
            └── output/           ← 处理结果
```

---

## 11. 常用命令速查

```bash
# ========== 环境相关 ==========
conda activate SmartCup                                    # 激活环境
conda run -n SmartCup python -u <脚本> [参数]               # 运行脚本（推荐方式）


# ========== AI 打标签（跨平台） ==========
# 试跑（检查数据和污染）
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --dry-run

# 正式运行（8 并发 + 断点续跑）
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --workers 8 --resume


# ========== 知乎 ==========
# 关键词搜索 + 自动爬取
conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯,恒温杯,Ember温控杯,华为水杯" --pages 5

# 仅搜索不爬取
conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯" --pages 3 --search-only

# 爬取已有链接列表
conda run -n SmartCup python -u -m source.zhihu_crawler.main

# 从头爬取（忽略进度）
conda run -n SmartCup python -u -m source.zhihu_crawler.main --no-resume


# ========== 抖音 ==========
# 关键词搜索 + 自动爬取（基础版）
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯,恒温杯,Ember温控杯" --pages 5

# 搜索 + 爬取 + 评论（完整版）
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯" --pages 5 --with-comments --comment-pages 5

# 仅搜索不爬取
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯" --pages 3 --search-only

# 按最新发布排序
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯" --pages 5 --sort 2

# 爬取已有链接列表
conda run -n SmartCup python -u -m source.douyin_crawler.main \
  --input res/data/douyin/raw/链接列表.csv


# ========== 格式转换（跨平台） ==========
# CSV → 格式化 Excel（知乎）
conda run -n SmartCup python source/cleandata/csv2xlsx.py res/data/zhihu/output/爬取结果.csv

# CSV → 格式化 Excel（抖音）
conda run -n SmartCup python source/cleandata/csv2xlsx.py res/data/douyin/output/爬取结果.csv
```

---

## 12. 如何分享给同门

### 12.1 同门需要的文件

把整个项目文件夹发给他（除了 `.env` 和 `res/data/`）。或者上传到 GitHub 后让他 clone。

### 12.2 同门需要做的

```bash
# 1. 安装 conda（同上）

# 2. 用 environment.yml 一键创建环境
conda env create -f environment.yml

# 3. 创建自己的 .env 文件
cp .env.example .env
# 然后编辑 .env，填入他的 DeepSeek Key 和各平台 Cookie

# 4. 放入自己的 CSV 数据到对应的 raw/ 目录

# 5. 运行！
# AI 打标签
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --workers 8 --resume

# 知乎爬虫
conda run -n SmartCup python -u -m source.zhihu_crawler.main

# 抖音爬虫
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯" --pages 5
```

### 12.3 如果有懂代码的朋友帮忙

在项目目录下创建 `CLAUDE.md`，内容是项目说明书（当前已有的那个文件）。这样使用 Claude Code 时，AI 助手会自动了解项目结构和命令，朋友帮忙改代码会更高效。

---

## 附录 A：关键概念解释

| 概念 | 通俗解释 |
|------|----------|
| **conda** | Python 的"沙盒"，每个项目一个独立环境，不会互相干扰 |
| **API** | 程序之间的接口。DeepSeek API = 把文字发给 DeepSeek，它返回分析结果 |
| **Cookie** | 浏览器的"身份证"，登录网站后浏览器携带这个来证明你是你 |
| **JSON** | 一种结构化的数据格式，程序好解析，人也能读 |
| **CSV** | 纯文本表格，用逗号分隔列 |
| **并发** | 同时做多件事。`--workers 8` = 同时发 8 条请求 |
| **断点续跑** | 中断后继续从上次停止的地方开始，不重复处理 |
| **反爬** | 网站检测并阻止爬虫的手段。限速 + 伪装成浏览器可以绕过 |
| **HTML** | 网页的源代码。爬虫下载 HTML，从中提取需要的信息 |
| **tqdm** | 进度条库，终端里显示"████░░░░ 45%"那种效果 |
| **a_bogus** | 抖音的反爬签名参数，每次请求都要携带 |
| **RENDER_DATA** | 抖音视频页面中内嵌的加密数据，包含视频的所有信息 |

## 附录 B：各平台爬虫对比一览

| 维度 | 知乎 | 抖音 |
|------|------|------|
| **请求延迟** | 2 秒 | 3 秒 |
| **最大并发** | 不限（建议 4-8） | 2（严格限制） |
| **签名机制** | 无 | a_bogus 签名 |
| **数据格式** | HTML 内嵌 JSON | RENDER_DATA 加密 |
| **Cookie 时效** | 较长（天级） | 较短（小时级） |
| **内容类型** | 问答/专栏/视频 | 视频/图文/直播 |
| **评论抓取** | 单独脚本 | 爬虫内置 |
| **互动指标** | 赞同+评论 | 点赞+评论+收藏+分享+播放 |
| **搜索方式** | HTML 解析 | API + 签名 |
