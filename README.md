# SmartCup — 知乎数据采集 & AI 标签分类

智能水杯/保温杯市场分析的完整数据工作流：

1. **搜索爬虫** — 关键词 → 自动搜索知乎 → 发现帖子
2. **内容爬虫** — 已有链接 → 爬取完整内容（13字段）
3. **AI 标签分类** — DeepSeek API 批量打标签 + 证据提取
4. **评论区爬取** — 问答帖评论区全量采集
5. **数据清洗** — 去污染、去重、排序、Excel 输出

## 快速开始

### 1. 环境安装

```bash
# 克隆项目
git clone <repo-url>
cd SmartCup

# 创建 conda 环境
conda env create -f environment.yml
conda activate SmartCup
```

### 2. 配置密钥

```bash
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key 和知乎 Cookie
```

### 3. 运行

```bash
# 关键词搜索 + 自动爬取
python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯, 恒温杯, Ember温控杯" --pages 5

# 基于已有链接列表爬取内容
python -u -m source.zhihu_crawler.main

# AI 批量打标签
python -u source/cleandata/batch_labeler.py --workers 8 --resume

# 爬取全部评论区
python -u source/cleandata/fetch_comments.py

# 数据清洗
python -u source/cleandata/clean_crawled.py
```

## 项目结构

```
SmartCup/
├── .env.example              # 密钥模板
├── environment.yml           # conda 环境配置
├── CLAUDE.md                 # AI 助手项目说明书
│
├── source/
│   ├── cleandata/            # 数据清洗 & AI 标签
│   │   ├── batch_labeler.py  # DeepSeek 批量标签分类
│   │   ├── fetch_comments.py # 评论区爬取
│   │   ├── clean_crawled.py  # 数据清洗
│   │   ├── csv2xlsx.py       # CSV → Excel
│   │   └── deepseek_filter.py
│   │
│   └── zhihu_crawler/        # 知乎爬虫
│       ├── main.py           # 链接爬虫入口
│       ├── search_main.py    # 搜索爬虫入口
│       ├── config.py
│       ├── items.py
│       ├── pipelines.py
│       ├── middleware.py
│       ├── utils.py
│       └── spiders/
│           ├── zhihu.py      # 核心爬虫（HTML解析）
│           └── search.py     # 搜索发现
│
└── res/data/zhihu/
    ├── raw/                  # 原始输入数据
    └── output/               # 处理结果
```

## AI 标签体系（21类）

智能水杯/温控杯、电热水杯/加热杯、Ember温控杯、其他国际智能品牌、麦开/Moikit、米家/小米水杯、华为/鸿蒙水杯、哈尔斯、苏泊尔、富光、希诺、物生物、膳魔师、象印、虎牌、Stanley、YETI、品牌对比/横评、保温杯推荐/导购、其他杯具相关、不相关

## 依赖

- Python 3.11+
- requests, beautifulsoup4, lxml, openpyxl, tqdm, python-dotenv
- DeepSeek API（标签分类）
- 知乎 Cookie（爬虫）
