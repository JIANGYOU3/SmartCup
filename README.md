# SmartCup — 智能水杯市场数据采集 & AI 标签分类

知乎 + 抖音双平台数据采集 + DeepSeek AI 自动打标签，完整的数据工作流。

---

## 管道流程

```
知乎搜索 ──┐
            ├──→ AI 标签分类（DeepSeek）──→ Excel 输出
抖音搜索 ──┘
```

1. **搜索爬虫** — 关键词 → 自动搜索 → 发现内容
2. **内容爬虫** — 已有链接 → 爬取完整详情（12~13 字段）
3. **数据清洗** — 去污染（NSFW/无关内容）、去重、排序
4. **AI 标签分类** — DeepSeek API 批量打标签（21 类）+ 证据提取
5. **评论区采集** — 问答帖/视频评论全量采集
6. **Excel 输出** — 统一格式的 .xlsx 文件

---

## 快速开始

### 1. 环境安装

```bash
git clone https://github.com/JIANGYOU3/SmartCup.git
cd SmartCup

# 创建 conda 环境
conda env create -f environment.yml
conda activate SmartCup
```

### 2. 配置密钥

```bash
cp .env.example .env
# 编辑 .env，填入：
#   DEEPSEEK_API_KEY=sk-xxxxx        （AI 打标签）
#   ZHIHU_COOKIE=...                 （知乎爬虫）
#   DOUYIN_COOKIE=...                （抖音爬虫）
```

### 3. 运行

```bash
# ──── 知乎 ────

# 关键词搜索 + 自动爬取
python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯,恒温杯,Ember温控杯" --pages 5

# 基于已有链接列表爬取
python -u -m source.zhihu_crawler.main

# ──── 抖音 ────

# 关键词搜索 + 自动爬取
python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯,恒温杯" --pages 5

# 仅搜索不爬取（先看结果）
python -u -m source.douyin_crawler.search_main \
  --keywords "智能水杯" --pages 3 --search-only

# ──── 数据清洗 & AI 打标签 ────

# 数据清洗（以知乎为例，抖音同理）
python source/cleandata/clean_crawled.py

# 爬取评论区
python source/cleandata/fetch_comments.py

# AI 批量打标签
python -u source/cleandata/batch_labeler.py --workers 8 --resume

# CSV 转 Excel
python source/cleandata/csv2xlsx.py res/data/zhihu/output/标签结果.csv
```

---

## 项目结构

```
SmartCup/
├── .env.example                    # 密钥模板
├── .gitignore
├── CLAUDE.md                       # AI 助手项目说明书
├── README.md
├── environment.yml                 # conda 环境配置
│
├── source/
│   ├── common/                     # 🆕 公共工具模块
│   │   ├── paths.py                #   统一项目根目录获取
│   │   ├── excel_style.py          #   Excel 样式封装
│   │   ├── text_utils.py           #   文本清洗 / 数字提取
│   │   ├── pollution.py            #   污染检测关键词
│   │   └── csv_utils.py            #   多行 CSV 解析
│   │
│   ├── cleandata/                  # 数据清洗 & AI 打标签
│   │   ├── batch_labeler.py        #   DeepSeek 批量标签分类（主脚本）
│   │   ├── deepseek_filter.py      #   DeepSeek 筛选过滤（旧版）
│   │   ├── clean_crawled.py        #   爬取结果清洗
│   │   ├── fetch_comments.py       #   评论区采集
│   │   └── csv2xlsx.py             #   CSV → Excel 转换
│   │
│   ├── zhihu_crawler/              # 知乎爬虫
│   │   ├── main.py                 #   入口：基于链接列表爬取
│   │   ├── search_main.py          #   入口：关键词搜索 + 自动爬取
│   │   ├── config.py               #   爬虫配置
│   │   ├── items.py                #   数据模型（ZhihuPost）
│   │   ├── pipelines.py            #   CSV / JSON 输出
│   │   ├── middleware.py           #   请求中间件
│   │   ├── utils.py                #   工具函数
│   │   └── spiders/
│   │       ├── zhihu.py            #   核心爬虫（HTML initialData 解析）
│   │       └── search.py           #   搜索爬虫（搜索 API）
│   │
│   └── douyin_crawler/             # 🆕 抖音爬虫
│       ├── main.py                 #   入口：基于链接列表爬取
│       ├── search_main.py          #   入口：关键词搜索 + 自动爬取
│       ├── config.py               #   爬虫配置
│       ├── items.py                #   数据模型（DouyinVideo）
│       ├── pipelines.py            #   CSV / JSON 输出
│       ├── sign/                   #   a_bogus 签名模块
│       │   ├── request.py          #     Request 类（自动签名）
│       │   ├── abogus_pure.py      #     纯 Python a_bogus 算法
│       │   ├── cookies.py          #     Cookie 管理
│       │   └── data/               #     签名映射表
│       └── spiders/
│           ├── douyin.py           #   核心爬虫（RENDER_DATA + API 双策略）
│           └── search.py           #   搜索爬虫（搜索 API）
│
└── res/data/
    ├── zhihu/
    │   ├── raw/                    # 知乎原始输入数据
    │   └── output/                 # 知乎处理结果
    └── douyin/
        ├── raw/                    # 抖音原始输入数据
        └── output/                 # 抖音处理结果
```

---

## AI 标签体系（21 类）

| 类别 | |
|------|---|
| 智能水杯/温控杯 | 电热水杯/加热杯 |
| Ember 温控杯 | 其他国际智能品牌 |
| 麦开/Moikit | 米家/小米水杯 |
| 华为/鸿蒙水杯 | 哈尔斯 |
| 苏泊尔 | 富光 |
| 希诺 | 物生物 |
| 膳魔师 | 象印 |
| 虎牌 | Stanley |
| YETI | 品牌对比/横评 |
| 保温杯推荐/导购 | 其他杯具相关 |
| 不相关 | — |

---

## 数据字段

### 知乎（13 字段）

关键词、帖子类型、问题被浏览次数、问题回答个数、问题评论个数、问题标题、问题内容、答主昵称、回答时间、赞同数、评论数、回答内容、问答链接

### 抖音（12 字段）

关键词、视频类型、播放数、评论数、视频标题、视频文案、作者昵称、发布时间、点赞数、分享数、视频时长、视频链接

---

## 依赖

- Python 3.10+
- requests, httpx, beautifulsoup4, lxml, openpyxl, tqdm, python-dotenv
- ujson, loguru（抖音签名模块）
- DeepSeek API（AI 标签分类）
- 知乎 Cookie + 抖音 Cookie（爬虫）
