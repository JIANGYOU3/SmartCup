# SmartCup — 智能水杯市场数据采集 & AI 标签分类

> **知乎 + 抖音双平台数据采集 + DeepSeek AI 自动打标签，完整的数据工作流。**
>
> 仓库地址：https://github.com/JIANGYOU3/SmartCup

---

## 📖 目录

- [项目简介](#项目简介)
- [环境准备（从零开始）](#环境准备从零开始)
  - [1. 安装 Git](#1-安装-git)
  - [2. 安装 Miniconda](#2-安装-miniconda)
  - [3. 安装 VS Code](#3-安装-vs-code)
  - [4. 配置 VS Code](#4-配置-vs-code)
- [克隆项目 & 创建环境](#克隆项目--创建环境)
- [配置密钥](#配置密钥)
- [项目结构](#项目结构)
- [数据管道流程](#数据管道流程)
- [使用指南](#使用指南)
  - [知乎爬虫](#知乎爬虫)
  - [抖音爬虫](#抖音爬虫)
  - [数据清洗 & AI 打标签](#数据清洗--ai-打标签)
- [AI 标签体系](#ai-标签体系)
- [数据字段说明](#数据字段说明)
- [技术架构](#技术架构)
- [常见问题](#常见问题)
- [AI 提示词模板](#ai-提示词模板)

---

## 项目简介

SmartCup 是一套完整的**智能水杯/保温杯市场分析数据管道**，能够：

1. **自动搜索** — 关键词 → 知乎/抖音搜索 → 发现内容
2. **内容爬取** — 已有链接 → 爬取完整详情（12~13 字段）
3. **数据清洗** — 去污染（NSFW/无关内容）、去重、排序
4. **AI 标签分类** — DeepSeek API 批量打标签（21 类）+ 证据提取
5. **评论区采集** — 问答帖/视频评论全量采集
6. **Excel 输出** — 统一格式的 `.xlsx` 文件，蓝色表头 + 冻结首行

## 环境准备（从零开始）

> 以下教程适用于 **Windows / macOS / Linux**，以 Windows 为例。

### 1. 安装 Git

**Git** 用于代码版本管理和克隆项目。

1. 打开 https://git-scm.com/downloads ，下载对应系统的安装包
2. 安装时一路点 "Next"（默认选项即可）
3. 安装完成后，打开 **终端**（Win+R → 输入 `cmd` → 回车），验证：

```bash
git --version
# 应该输出: git version 2.xx.x
```

4. 配置 Git 用户信息（替换成你自己的）：

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"
```

---

### 2. 安装 Miniconda

**Miniconda** 用于创建隔离的 Python 虚拟环境，避免依赖冲突。

#### 2.1 下载安装

1. 打开 https://docs.anaconda.com/miniconda/ ，下载最新版 Miniconda
   - Windows 选 `Miniconda3 Windows 64-bit`
   - macOS 选 `Miniconda3 macOS Apple M1 64-bit pkg`（M 芯片）或 `Intel x86`（Intel 芯片）
   - Linux 选 `Miniconda3 Linux 64-bit`
2. 安装：
   - **Windows**：双击 `.exe`，一路 Next。⚠️ **重要**：勾选 "Add Miniconda3 to PATH"（安装程序会提示不推荐，但勾选后更方便）
   - **macOS**：双击 `.pkg`，按提示安装
   - **Linux**：终端运行 `bash Miniconda3-latest-Linux-x86_64.sh`，一路 Enter，最后选 `yes` 初始化

#### 2.2 配置 conda 镜像（国内用户加速下载）

打开终端，运行以下命令添加清华镜像源：

```bash
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --set show_channel_urls yes
```

#### 2.3 验证安装

关闭终端重新打开，运行：

```bash
conda --version
# 应该输出: conda 24.x.x
```

---

### 3. 安装 VS Code

**VS Code** 是推荐的代码编辑器。

1. 打开 https://code.visualstudio.com/ ，下载安装
2. 安装时建议勾选：
   - ✅ "Add 'Open with Code' action to Windows Explorer file context menu"
   - ✅ "Add 'Open with Code' action to Windows Explorer directory context menu"
   - ✅ "Register Code as an editor for supported file types"
   - ✅ "Add to PATH"

---

### 4. 配置 VS Code

#### 4.1 必装扩展

打开 VS Code，点击左侧 **Extensions**（`Ctrl+Shift+X`），搜索并安装以下扩展：

| 扩展名 | 用途 |
|--------|------|
| **Python** (ms-python.python) | Python 语法高亮、调试、环境管理 |
| **Python Debugger** (ms-python.debugpy) | Python 调试器 |
| **Pylance** (ms-python.vscode-pylance) | Python 智能提示、类型检查 |
| **GitLens** (eamodio.gitlens) | Git 可视化增强 |

> 可选但推荐：
> - **Chinese (Simplified) Language Pack** — 中文界面
> - **Rainbow CSV** — CSV 文件高亮着色
> - **Even Better TOML** — `.env` 文件语法高亮
> - **Markdown Preview Enhanced** — Markdown 预览

#### 4.2 VS Code 设置

打开 VS Code 设置（`Ctrl+,`），点击右上角 "Open Settings (JSON)"，添加以下配置：

```json
{
    // Python 环境管理器设为 conda
    "python-envs.defaultEnvManager": "ms-python.python:conda",
    "python-envs.defaultPackageManager": "ms-python.python:conda",

    // 自动选择项目 conda 环境
    "python.terminal.activateEnvironment": true,

    // 保存时自动格式化
    "editor.formatOnSave": true,

    // 文件自动保存
    "files.autoSave": "onFocusChange",

    // 终端使用 PowerShell（Windows）/ bash（macOS/Linux）
    "terminal.integrated.defaultProfile.windows": "PowerShell",
    "terminal.integrated.defaultProfile.linux": "bash",
    "terminal.integrated.defaultProfile.osx": "zsh"
}
```

#### 4.3 选择 Python 解释器

1. `Ctrl+Shift+P` → 输入 `Python: Select Interpreter`
2. 选择 `SmartCup` (conda) — 如果你已经创建好环境的话（下一步创建）

---

## 克隆项目 & 创建环境

### 步骤 1：克隆仓库

打开终端（VS Code 内按 `` Ctrl+` ``），定位到你的工作目录：

```bash
# 进入你存放代码的目录（例如桌面下的 projects 文件夹）
cd ~/Desktop
mkdir projects
cd projects

# 克隆项目
git clone https://github.com/JIANGYOU3/SmartCup.git
cd SmartCup
```

### 步骤 2：创建 conda 环境

项目提供了 `environment.yml`，可以直接创建完全一致的环境：

```bash
# 从 environment.yml 创建环境（首次需要下载依赖，约 3-5 分钟）
conda env create -f environment.yml

# 激活环境
conda activate SmartCup
```

如果创建失败或需要更新环境：

```bash
# 更新已有环境
conda env update -f environment.yml --prune
```

### 步骤 3：用 VS Code 打开项目

```bash
# 在项目目录下，用 VS Code 打开
code .
```

VS Code 右下角应该显示 `SmartCup` (conda) 环境。如果不是，按 **4.3** 节手动选择。

### 步骤 4：验证环境

在 VS Code 终端（`` Ctrl+` ``）中运行：

```bash
conda activate SmartCup
python -c "import requests, httpx, bs4, lxml, openpyxl, tqdm, dotenv; print('✅ 环境就绪')"
```

如果输出 `✅ 环境就绪`，说明一切正常。

> 如果提示缺少模块，手动安装：
> ```bash
> pip install httpx ujson loguru
> ```

---

## 配置密钥

项目依赖 3 个外部服务，需要在项目根目录创建 `.env` 文件。

### 创建 .env 文件

```bash
# 复制模板
cp .env.example .env
```

### 编辑 .env

在 VS Code 中打开 `.env` 文件，填入以下内容：

```env
# ─── DeepSeek API Key（AI 标签分类）───
# 注册地址：https://platform.deepseek.com
# 注册后在 "API Keys" 页面创建 Key
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ─── 知乎 Cookie（知乎爬虫）───
# 获取方式：
#   1. 浏览器打开 www.zhihu.com 并登录
#   2. F12 → Application → Cookies → www.zhihu.com
#   3. 将下列关键 cookie 拼接或用完整 cookie 字符串
ZHIHU_COOKIE=你的知乎cookie字符串

# ─── 抖音 Cookie（抖音爬虫）───
# 获取方式：
#   1. 浏览器打开 www.douyin.com 并扫码登录
#   2. F12 → Application → Cookies → www.douyin.com
#   3. 复制所有 cookie 键值对，格式: key1=value1; key2=value2; ...
DOUYIN_COOKIE=你的抖音cookie字符串
```

### 各 Cookie 获取详细步骤

#### 知乎 Cookie

1. 浏览器打开 [www.zhihu.com](https://www.zhihu.com)，扫码/密码登录
2. 按 `F12` 打开开发者工具
3. 进入 **Application** 标签 → 左侧 **Cookies** → 点击 `www.zhihu.com`
4. 复制完整的 cookie 字符串（浏览器地址栏输入 `javascript:document.cookie` 也可以快速获取）
5. 粘贴到 `.env` 的 `ZHIHU_COOKIE=` 后面
6. ⚠️ 知乎 Cookie **有效期约 30 天**，过期需重新获取

#### 抖音 Cookie

1. 浏览器打开 [www.douyin.com](https://www.douyin.com)，扫码登录
2. 按 `F12` 打开开发者工具
3. 进入 **Application** 标签 → 左侧 **Cookies** → 点击 `www.douyin.com`
4. 找到所有 cookie，手动拼接为 `key1=value1; key2=value2; ...` 格式
5. 粘贴到 `.env` 的 `DOUYIN_COOKIE=` 后面
6. ⚠️ 抖音 Cookie **有效期很短（几小时到 1 天）**，过期需重新获取

#### DeepSeek API Key

1. 打开 [platform.deepseek.com](https://platform.deepseek.com)
2. 注册账号（手机号注册）
3. 进入 **API Keys** 页面，点击 "创建 API Key"
4. 复制 Key 填入 `.env`

---

## 项目结构

```
SmartCup/
├── .env                          # 🔐 密钥配置（不提交到 Git）
├── .env.example                  # 密钥模板（参考用）
├── .gitignore                    # Git 忽略规则
├── CLAUDE.md                     # 🤖 AI 助手项目说明书（AI 读这个了解项目）
├── README.md                     # 📖 本文件（人类读的教程）
├── environment.yml               # conda 环境依赖清单
│
├── source/                       # 📦 源代码
│   ├── common/                   # 🧩 公共工具模块
│   │   ├── paths.py              #   统一项目根目录获取 & .env 加载
│   │   ├── excel_style.py        #   Excel 样式封装（蓝色表头/冻结/链接样式）
│   │   ├── text_utils.py         #   文本清洗（控制字符/HTML实体）/ 数字提取
│   │   ├── pollution.py          #   污染检测关键词（NSFW/体育奖杯/不相关）
│   │   └── csv_utils.py          #   跨行 CSV 解析 / 链接提取
│   │
│   ├── cleandata/                # 🧹 数据清洗 & AI 打标签
│   │   ├── batch_labeler.py      #   ⭐ DeepSeek 批量标签分类（主脚本）
│   │   ├── deepseek_filter.py    #   DeepSeek 筛选过滤（旧版，单条判断）
│   │   ├── clean_crawled.py      #   爬取结果清洗（去视频/NSFW/短内容）
│   │   ├── fetch_comments.py     #   评论区采集（知乎 API）
│   │   └── csv2xlsx.py           #   CSV → Excel 转换工具
│   │
│   ├── zhihu_crawler/            # 🌐 知乎爬虫
│   │   ├── main.py               #   入口：基于已有链接列表爬取
│   │   ├── search_main.py        #   入口：关键词搜索 + 自动爬取
│   │   ├── config.py             #   爬虫配置（请求间隔/并发/Cookie）
│   │   ├── items.py              #   数据模型（ZhihuPost dataclass）
│   │   ├── pipelines.py          #   CSV / JSON 输出管道
│   │   ├── middleware.py         #   请求中间件（Headers/延迟）
│   │   ├── utils.py              #   工具函数（重试/哈希）
│   │   └── spiders/
│   │       ├── zhihu.py          #   核心爬虫（HTML initialData 解析）
│   │       └── search.py         #   搜索爬虫（搜索 API）
│   │
│   └── douyin_crawler/           # 🎵 抖音爬虫
│       ├── main.py               #   入口：基于已有链接列表爬取
│       ├── search_main.py        #   入口：关键词搜索 + 自动爬取
│       ├── config.py             #   爬虫配置
│       ├── items.py              #   数据模型（DouyinVideo dataclass）
│       ├── pipelines.py          #   CSV / JSON 输出管道
│       ├── sign/                 #   🔐 a_bogus 签名模块
│       │   ├── request.py        #     Request 类（自动签名 + 请求）
│       │   ├── abogus_pure.py    #     纯 Python a_bogus 生成（查表法）
│       │   ├── cookies.py        #     Cookie 管理（字符串↔字典）
│       │   ├── util.py           #     JSON 保存 / URL 工具
│       │   └── data/             #     签名映射表
│       └── spiders/
│           ├── douyin.py         #   核心爬虫（RENDER_DATA + API 双策略）
│           └── search.py         #   搜索爬虫（搜索 API）
│
└── res/data/                     # 📊 数据文件
    ├── zhihu/
    │   ├── raw/                  # 知乎原始输入数据（链接列表 CSV）
    │   │   └── 标题筛选版1.0.csv
    │   └── output/               # 知乎处理结果
    │       ├── 爬取结果.csv
    │       ├── 爬取结果_清洗后.csv
    │       ├── 爬取结果_含评论.csv
    │       ├── 标签结果.csv
    │       └── *.xlsx
    └── douyin/
        ├── raw/                  # 抖音原始输入数据
        └── output/               # 抖音处理结果
```

---

## 数据管道流程

```
                     ┌──────────────┐
                     │  关键词输入   │
                     └──────┬───────┘
                            │
            ┌───────────────┼───────────────┐
            ▼                               ▼
    ┌───────────────┐               ┌───────────────┐
    │  知乎搜索爬虫  │               │  抖音搜索爬虫  │
    │  search_main   │               │  search_main   │
    └───────┬───────┘               └───────┬───────┘
            │                               │
            ▼                               ▼
    ┌───────────────┐               ┌───────────────┐
    │  搜索结果 CSV  │               │  搜索结果 CSV  │
    │  (链接+摘要)   │               │  (链接+描述)   │
    └───────┬───────┘               └───────┬───────┘
            │                               │
            ▼                               ▼
    ┌───────────────┐               ┌───────────────┐
    │  内容爬虫      │               │  内容爬虫      │
    │  main.py       │               │  main.py       │
    │  (13 字段)     │               │  (12 字段)     │
    └───────┬───────┘               └───────┬───────┘
            │                               │
            ▼                               ▼
    ┌───────────────┐               ┌───────────────┐
    │  clean_crawled │               │  CSV + Excel  │
    │  (清洗)        │               │  (自动输出)    │
    └───────┬───────┘               └───────────────┘
            │
            ▼
    ┌───────────────┐
    │ fetch_comments │ ← 可选：爬取评论区
    │ (评论采集)     │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ batch_labeler  │
    │ DeepSeek AI    │
    │ (21类标签+证据)│
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │  Excel 输出    │
    │  标签结果.xlsx │
    └───────────────┘
```

---

## 使用指南

> ⚠️ 所有命令都在项目根目录（`SmartCup/`）下运行。
> 确保先 `conda activate SmartCup` 激活环境。

### 知乎爬虫

#### 关键词搜索 + 自动爬取

```bash
conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯,恒温杯,Ember温控杯,华为水杯" \
  --pages 5
```

- `--keywords`：搜索关键词，多个用逗号分隔
- `--pages`：每个关键词翻几页（每页 20 条，5 页 = 100 条/关键词）
- `-u`：禁用 Python 输出缓冲，确保进度条实时显示

#### 仅搜索不爬取（先看找到了什么）

```bash
conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯" --pages 3 --search-only
```

#### 基于已有链接列表爬取

```bash
conda run -n SmartCup python -u -m source.zhihu_crawler.main
```

默认读取 `res/data/zhihu/raw/标题筛选版1.0.csv`，输出到 `res/data/zhihu/output/爬取结果.csv`。

#### 知乎爬虫支持的链接类型

| URL 格式 | 类型 | 解析方式 |
|----------|------|---------|
| `/question/{qid}/answer/{aid}` | 问答帖 | HTML `js-initialData` → entities.answers + questions |
| `/question/{qid}` | 问题帖 | HTML `js-initialData` → entities.questions |
| `/p/{post_id}` | 专栏文章 | HTML `js-initialData` → entities.articles / post |
| `/zvideo/{id}` | 视频 | ⏭️ 跳过（无文字内容） |

---

### 抖音爬虫

#### 关键词搜索 + 自动爬取

```bash
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯,恒温杯,Ember温控杯" \
  --pages 5
```

#### 仅搜索不爬取

```bash
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯" --pages 3 --search-only
```

#### 基于已有链接列表爬取

```bash
conda run -n SmartCup python -u -m source.douyin_crawler.main \
  --input res/data/douyin/raw/链接列表.csv \
  --output res/data/douyin/output/爬取结果.csv
```

#### 抖音爬虫技术细节

采用**双策略**保证数据完整性：

| 策略 | 方式 | 说明 |
|------|------|------|
| **A（优先）** | 解析 HTML `<script id="RENDER_DATA">` SSR JSON | 首屏数据，无需签名，速度快 |
| **B（补充）** | API `/aweme/v1/web/aweme/detail/` | 需要 a_bogus 签名，补充策略 A 缺失的字段 |

- a_bogus 签名：纯 Python 查表法实现（`sign/abogus_pure.py`），无需 Node.js
- 反爬：请求间隔 3 秒，并发数 2（抖音反爬严格）

---

### 数据清洗 & AI 打标签

#### 1. 清洗爬取结果

```bash
conda run -n SmartCup python source/cleandata/clean_crawled.py
```

清洗规则：
- ❌ 视频类（无文字内容）
- ❌ 空内容
- ❌ NSFW（成人用品等）
- ❌ 短内容无互动（<20 字且 0 赞 0 评）

#### 2. 爬取评论区（可选）

```bash
conda run -n SmartCup python source/cleandata/fetch_comments.py
```

筛选评论数 > 0 的问答帖，调用知乎评论 API 采集评论。

#### 3. AI 批量标签分类

```bash
# 正式运行（8 并发）
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --workers 8 --resume

# Dry-run 测试（不调 API，仅预览）
conda run -n SmartCup python source/cleandata/batch_labeler.py --dry-run

# 断点续跑（从上次中断位置继续）
conda run -n SmartCup python source/cleandata/batch_labeler.py --workers 8 --resume
```

- `--workers 8`：8 个并发请求（DeepSeek 付费账户安全值）
- `--resume`：支持断点续跑，中断后自动恢复
- 每处理 20 条自动保存进度，防止数据丢失

#### 4. CSV 转 Excel

```bash
conda run -n SmartCup python source/cleandata/csv2xlsx.py res/data/zhihu/output/标签结果.csv
```

Excel 自动格式化：蓝色表头 + 冻结首行 + 自动筛选 + 链接列超链接样式。

---

## AI 标签体系（21 类）

| 类别 | 说明 |
|------|------|
| **智能水杯/温控杯** | 智能控温、恒温、调温功能的水杯 |
| **电热水杯/加热杯** | 便携电热水杯、车载加热杯、55度杯 |
| **Ember 温控杯** | Ember 品牌温控马克杯 |
| **其他国际智能品牌** | OHOM / Nextmug / Cauldryn / HidrateSpark / LARQ |
| **麦开/Moikit** | 麦开智能水杯 |
| **米家/小米水杯** | 小米、米家生态水杯 |
| **华为/鸿蒙水杯** | 华为智选、鸿蒙智联水杯 |
| **哈尔斯** | 哈尔斯品牌（智能/保温系列） |
| **苏泊尔** | 苏泊尔品牌水杯 |
| **富光** | 富光品牌水杯 |
| **希诺** | 希诺品牌水杯 |
| **物生物** | 物生物品牌水杯 |
| **膳魔师** | 膳魔师 / Thermos |
| **象印** | 象印 / Zojirushi |
| **虎牌** | 虎牌 / Tiger |
| **Stanley** | Stanley 品牌 |
| **YETI** | YETI 品牌 |
| **品牌对比/横评** | 多个品牌或产品的横向对比/测评 |
| **保温杯推荐/导购** | 保温杯选购指南、推荐清单 |
| **其他杯具相关** | 与水杯相关但不属于上述品牌/类型 |
| **不相关** | 与水杯/上述品牌无关的内容 |

---

## 数据字段说明

### 知乎输出（13 字段）

| 字段 | 说明 | 示例 |
|------|------|------|
| 关键词 | 话题标签 | 智能水杯, 恒温杯 |
| 帖子类型 | 问答帖 / 问题帖 / 专栏文章 / 视频 | 问答帖 |
| 问题被浏览次数 | 问题浏览量 | 12345 |
| 问题回答个数 | 回答总数 | 67 |
| 问题评论个数 | 问题评论数 | 12 |
| 问题标题 | 问题标题文本 | 智能水杯值得买吗？ |
| 问题内容 | 问题详细描述 | 最近想买一个... |
| 答主昵称 | 作者昵称 | 张三 |
| 回答时间 | 发布时间 | 2025-06-15 14:30 |
| 赞同数 | 点赞数 | 256 |
| 评论数 | 评论数 | 89 |
| 回答内容 | 回答正文 | 作为一个用过三款... |
| 问答链接 | 原始链接 | https://www.zhihu.com/question/... |

### 抖音输出（12 字段）

| 字段 | 说明 | 示例 |
|------|------|------|
| 关键词 | 搜索关键词 | 智能水杯 |
| 视频类型 | 短视频 / 图文 / 直播 | 短视频 |
| 播放数 | 播放量 | 12345 |
| 评论数 | 评论数 | 89 |
| 视频标题 | 视频描述 | 智能水杯开箱测评 |
| 视频文案 | 完整描述文本 | 今天给大家... |
| 作者昵称 | 发布者 | 科技小明 |
| 发布时间 | 发布时间 | 2025-06-15 14:30:00 |
| 点赞数 | 点赞数 | 1234 |
| 分享数 | 分享数 | 56 |
| 视频时长 | 视频时长（秒） | 60 |
| 视频链接 | 原始链接 | https://www.douyin.com/video/... |

### AI 标签输出（7 字段）

| 字段 | 说明 |
|------|------|
| 链接 | 原始知乎链接 |
| 标签 | AI 打的标签（可多个，逗号分隔） |
| 标题 | 清洗后的标题 |
| 正文开头 | 正文前 200 字 |
| 点赞数 | 赞同数 |
| 评论数 | 评论数 |
| AI证据理由 | AI 从原文引用的证据 |

---

## 技术架构

### 技术栈

| 层 | 技术 |
|----|------|
| 语言 | Python 3.10+ |
| 环境管理 | Conda (Miniconda) |
| HTTP 请求 | requests, httpx |
| HTML 解析 | BeautifulSoup4 + lxml |
| JSON 处理 | ujson (抖音签名模块) |
| Excel 操作 | openpyxl |
| AI 接口 | DeepSeek API (deepseek-chat) |
| 进度显示 | tqdm |
| 日志 | loguru (抖音模块) |
| 配置管理 | python-dotenv (.env 文件) |

### 设计模式

- **双策略解析**：HTML SSR 解析 + API 补充，保证数据完整性
- **管道模式**：搜索 → 爬取 → 清洗 → AI 标签 → Excel，每个阶段解耦独立
- **断点续跑**：支持中断后恢复，每 20 条自动保存进度
- **公共模块提取**：`source/common/` 消除重复代码（Excel 样式、文本清洗、污染检测）
- **签名自动化**：抖音 API 请求自动附加 a_bogus 签名，调用方无需关心

### 并发与反爬策略

| 平台 | 并发数 | 请求间隔 | 说明 |
|------|--------|----------|------|
| 知乎 | 4（串行） | 2-3 秒 | 相对宽松 |
| 抖音 | 2（串行） | 3-4 秒 | 反爬严格，低并发 |
| DeepSeek API | 8 | — | 付费账户安全值 |

---

## 常见问题

### Q: conda 环境创建失败？

```bash
# 更新 conda
conda update -n base conda

# 清理缓存后重试
conda clean --all
conda env create -f environment.yml
```

### Q: 提示缺少模块？

```bash
conda activate SmartCup
pip install httpx ujson loguru
```

### Q: 知乎爬虫返回 403？

Cookie 过期或无效。重新从浏览器获取知乎 Cookie，更新 `.env`。

### Q: 抖音爬虫返回空数据？

可能原因：
1. Cookie 过期（抖音 Cookie 有效期很短，需频繁更新）
2. a_bogus 签名映射表过期（更新 `sign/data/time_mapping.json`）

### Q: DeepSeek API 调用失败？

1. 检查 `.env` 中 API Key 是否正确
2. 检查账户余额是否充足（https://platform.deepseek.com）
3. 确认网络能访问 `api.deepseek.com`

### Q: VS Code 终端无法激活 conda？

```powershell
# PowerShell（Windows）
conda init powershell
# 关闭终端重新打开

# bash（Linux/macOS）
conda init bash
# 关闭终端重新打开
```

### Q: Git 推送失败 "Permission denied"？

需要配置 GitHub SSH Key 或使用 Personal Access Token：

```bash
# 方案 1：SSH Key（推荐）
ssh-keygen -t ed25519 -C "你的邮箱"
cat ~/.ssh/id_ed25519.pub
# 将输出的公钥添加到 GitHub → Settings → SSH Keys

# 方案 2：Personal Access Token
# GitHub → Settings → Developer settings → Tokens (classic) → Generate
# 使用 token 代替密码
```

---

## AI 提示词模板

> 📋 **使用方式**：将以下内容复制给任意 AI（ChatGPT、Claude、Gemini 等），
> AI 即可理解整个项目并协助开发和维护。

````markdown
# SmartCup 项目 AI 提示词

你是一个 Python 数据采集 & AI 标签分类项目的开发助手。请仔细阅读以下项目说明。

## 项目概述

SmartCup 是一个智能水杯/保温杯市场分析工具，支持知乎 + 抖音双平台数据采集，使用 DeepSeek API 进行 AI 自动标签分类。

GitHub 仓库：https://github.com/JIANGYOU3/SmartCup

## 技术栈

- Python 3.10+，conda 环境名为 `SmartCup`
- requests, httpx, BeautifulSoup4, lxml, openpyxl, tqdm, python-dotenv, ujson, loguru
- DeepSeek API (deepseek-chat) 用于 AI 标签分类
- 知乎/抖音 Cookie 用于爬虫认证

## 项目结构

```
SmartCup/
├── .env                          # API Key & Cookie（通过 python-dotenv 加载）
├── environment.yml               # conda 环境配置
├── source/
│   ├── common/                   # 公共工具模块
│   │   ├── paths.py              #   项目根目录获取、.env 加载
│   │   ├── excel_style.py        #   Excel 样式封装（apply_excel_style, csv_to_excel）
│   │   ├── text_utils.py         #   clean_text, extract_number, make_content_preview
│   │   ├── pollution.py          #   is_polluted（NSFW/体育奖杯检测）
│   │   └── csv_utils.py          #   parse_multiline_csv, extract_links_from_csv
│   ├── cleandata/
│   │   ├── batch_labeler.py      #   DeepSeek API 批量标签分类（21类+证据）
│   │   ├── deepseek_filter.py    #   旧版二分类筛选
│   │   ├── clean_crawled.py      #   清洗爬取结果
│   │   ├── fetch_comments.py     #   知乎评论区采集
│   │   └── csv2xlsx.py           #   CSV→Excel 转换
│   ├── zhihu_crawler/
│   │   ├── main.py               #   基于链接列表爬取入口
│   │   ├── search_main.py        #   关键词搜索+爬取入口
│   │   ├── config.py             #   配置（延迟/并发/Cookie）
│   │   ├── items.py              #   ZhihuPost dataclass
│   │   ├── pipelines.py          #   CsvPipeline / JsonPipeline
│   │   ├── middleware.py         #   请求中间件
│   │   ├── utils.py              #   clean_text, extract_number, retry
│   │   └── spiders/
│   │       ├── zhihu.py          #   ZhihuScraper（HTML initialData 解析）
│   │       └── search.py         #   ZhihuSearcher（搜索API）+ search_and_crawl
│   └── douyin_crawler/
│       ├── main.py               #   基于链接列表爬取入口
│       ├── search_main.py        #   关键词搜索+爬取入口
│       ├── config.py             #   配置
│       ├── items.py              #   DouyinVideo dataclass
│       ├── pipelines.py          #   CsvPipeline / JsonPipeline
│       ├── sign/                 #   a_bogus 签名模块
│       │   ├── request.py        #     Request 类（getJSON 自动签名）
│       │   ├── abogus_pure.py    #     纯 Python a_bogus 生成
│       │   ├── cookies.py        #     Cookie 管理
│       │   └── util.py           #     JSON 保存
│       └── spiders/
│           ├── douyin.py         #   DouyinScraper（RENDER_DATA + API 双策略）
│           └── search.py         #   DouyinSearcher（搜索API）
└── res/data/
    ├── zhihu/{raw,output}/
    └── douyin/{raw,output}/
```

## 运行命令

所有命令在项目根目录运行，使用 `conda run -n SmartCup python` 或先 `conda activate SmartCup`。

### 知乎

```bash
# 关键词搜索 + 自动爬取（-u 禁用缓冲确保进度条正常）
conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯,恒温杯" --pages 5

# 仅搜索
conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯" --pages 3 --search-only

# 基于已有链接爬取
conda run -n SmartCup python -u -m source.zhihu_crawler.main
```

### 抖音

```bash
# 关键词搜索 + 爬取
conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯,恒温杯" --pages 5

# 基于已有链接爬取
conda run -n SmartCup python -u -m source.douyin_crawler.main
```

### 数据清洗 & AI

```bash
# AI 标签分类
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --workers 8 --resume

# 清洗
conda run -n SmartCup python source/cleandata/clean_crawled.py

# 评论采集
conda run -n SmartCup python source/cleandata/fetch_comments.py

# CSV → Excel
conda run -n SmartCup python source/cleandata/csv2xlsx.py <csv路径>
```

## 关键设计决策

1. **知乎爬虫使用 HTML 解析而非 API**：一次 HTML 请求获取所有字段（通过 js-initialData），避免多次 API 调用的频率限制
2. **抖音爬虫双策略**：优先从 RENDER_DATA SSR JSON 提取（无需签名），缺失字段再用 API 补充
3. **a_bogus 纯 Python 查表实现**：不依赖 Node.js，但映射表可能需要定期更新
4. **DeepSeek 使用 JSON Mode**：`response_format: {"type": "json_object"}` 确保输出可解析
5. **断点续跑**：labeler 和爬虫都支持，进度保存在输出目录的 JSON 文件中
6. **所有脚本通过 `source/common/paths.py` 获取项目根目录**，不依赖 `os.getcwd()`
7. **Excel 样式统一封装**：蓝色表头(4472C4) + 微软雅黑 + 冻结首行 + 自动筛选

## 环境变量（.env）

```
DEEPSEEK_API_KEY=sk-xxxxx          # DeepSeek API Key
ZHIHU_COOKIE=xxx; yyy; zzz         # 知乎 Cookie 字符串
DOUYIN_COOKIE=xxx; yyy; zzz        # 抖音 Cookie 字符串
```

Cookie 通过 `python-dotenv` 加载，从 `os.getenv()` 读取。

## 注意事项

- 抖音 Cookie 有效期短（几小时），需频繁更新
- 知乎 Cookie 有效期约 30 天
- 抖音并发数默认 2（反爬严格），知乎默认 4
- DeepSeek 并发默认 8（付费账户安全值）
- 所有爬虫输出 CSV 使用 `utf-8-sig` 编码（兼容 Excel 打开中文）
- `.gitignore` 忽略 `.env`、数据文件、进度文件

请基于以上信息协助开发和维护本项目。
````

---

## 许可证

本项目仅供学习和研究使用。请遵守知乎和抖音的 robots.txt 及服务条款，合理控制爬取频率。

---

> 💡 **快速开始只需 4 步**：装 conda → 克隆项目 → 创建环境 → 填 `.env` → 运行！
