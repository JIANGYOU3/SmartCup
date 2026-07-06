"""CSV → Excel 转换工具"""
import sys
from pathlib import Path
from source.common.excel_style import csv_to_excel

csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("res/data/标签结果.csv")

excel_path = csv_to_excel(
    csv_path,
    sheet_title="标签结果",
    column_widths={
        "链接": 35, "标签": 30, "标题": 45, "正文开头": 50,
        "点赞数": 10, "评论数": 10, "AI证据理由": 55, "AI原始JSON": 45,
    },
    link_columns={"链接"},
    number_columns={"点赞数", "评论数"},
)
print(f"✅ Excel 已保存: {excel_path}")
