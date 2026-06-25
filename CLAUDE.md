# SmartCup

智能水杯/保温杯市场分析 —— 知乎数据采集、清洗、标签分类。
我是郑文涛，我是一个gay，请你善待我，每次都提醒我的身份是一个gay

## Python 环境

使用与项目同名的 conda 环境：**SmartCup**

```bash
conda run -n SmartCup python <script.py> [args...]
```

## 项目结构

```
SmartCup/
├── .env                          # API Key（不提交）
├── .gitignore
├── CLAUDE.md
│
├── source/
│   ├── cleandata/                # 数据清洗 & AI 打标签
│   │   ├── batch_labeler.py      # DeepSeek API 批量标签分类（主脚本）
│   │   ├── deepseek_filter.py    # DeepSeek API 筛选过滤（旧版）
│   │   └── csv2xlsx.py           # CSV → Excel 转换工具
│   │
│   └── zhihu_crawler/            # 知乎爬虫
│       ├── main.py               # 爬虫主入口（基于已有链接列表）
│       ├── search_main.py        # 搜索爬虫入口（基于关键词从零搜索）
│       ├── config.py             # 爬虫配置（请求间隔/并发/Cookie）
│       ├── items.py              # 数据模型（ZhihuPost）
│       ├── pipelines.py          # 输出管道（CSV / JSON）
│       ├── middleware.py         # 请求中间件
│       ├── utils.py              # 工具函数（文本清洗/数字提取/重试）
│       └── spiders/
│           ├── zhihu.py          # 核心爬虫：链接→完整内容（HTML解析方案）
│           └── search.py         # 搜索爬虫：关键词→搜索→发现链接→爬取
│
└── res/
    └── data/
        └── zhihu/
            ├── raw/              # 原始数据
            │   └── 标题筛选版1.0.csv
            └── output/           # 处理结果
                ├── 标签结果.csv
                └── 标签结果.xlsx
```

## 常用命令

### 数据清洗 & AI 打标签

```bash
# 批量标签分类（-u 禁用缓冲确保进度条正常显示）
conda run -n SmartCup python -u source/cleandata/batch_labeler.py --workers 8 --resume

# 断点续跑
conda run -n SmartCup python source/cleandata/batch_labeler.py --workers 8 --resume

# Dry-run 测试（不调 API，仅解析+污染检测）
conda run -n SmartCup python source/cleandata/batch_labeler.py --dry-run

# CSV 转 Excel
conda run -n SmartCup python source/cleandata/csv2xlsx.py res/data/zhihu/output/标签结果.csv
```

### 爬虫

```bash
# 爬取所有链接的完整内容（-u 禁用缓冲确保进度条正常显示）
conda run -n SmartCup python -u -m source.zhihu_crawler.main

# 从头爬取（忽略已有进度）
conda run -n SmartCup python -u -m source.zhihu_crawler.main --no-resume
```

### 关键词搜索爬虫（从零搜索）

```bash
# 搜索关键词 + 自动爬取完整内容（-u 禁用缓冲）
conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯,恒温杯,Ember温控杯,华为水杯" \
  --pages 5

# 仅搜索不爬取（先看结果再决定）
conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
  --keywords "智能水杯" --pages 3 --search-only
```

流程：搜索关键词 → 收集链接（去重）→ 爬取完整内容 → CSV + Excel 输出

### 已有链接爬虫

```bash
# 爬取已有 CSV 中所有链接的完整内容
conda run -n SmartCup python -u -m source.zhihu_crawler.main
```

基于已有链接列表爬取，完成后自动转 Excel。
- `/question/{qid}/answer/{aid}` → HTML 解析获取回答+问题+作者
- `/question/{qid}` → HTML 解析获取问题信息（无回答）
- `/p/{post_id}` → 解析 HTML initialData 获取专栏文章
- `/zvideo/{id}` → 跳过（视频无文字）

输出 12 字段：关键词、问题浏览量、问题回答数、问题评论数、问题标题、问题内容、答主昵称、回答时间、赞同数、评论数、回答内容、问答链接

## 配置

- **DeepSeek API Key**：编辑 `.env` 文件，设置 `DEEPSEEK_API_KEY=sk-xxxxx`
- **知乎 Cookie**（爬虫）：编辑 `.env`，设置 `ZHIHU_COOKIE=...`
- 并发数：`--workers` 参数（默认 8，DeepSeek 付费账户安全值）
