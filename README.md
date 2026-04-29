# Journal Issue Abstract Extractor

给一个“期刊某一期(issue)”链接，自动抓取该期下文章的 abstract，并导出结构化文献表（每篇一行）。

## 输出字段
- `title`
- `journal`
- `author`
- `abstract`（原文）
- `conclusion`
- `Y`
- `X`
- `IV`
- `data`
- `method`
- `country`
- `population`
- `source_url`

> 说明：`conclusion / Y / X / IV / data / method / country / population` 基于 abstract 的启发式规则抽取，建议人工复核。

## 安装
```bash
pip install -r requirements.txt
```

## 使用
导出 CSV（默认推荐，不依赖 pandas）：
```bash
python journal_issue_abstract_extractor.py "https://<journal-site>/issue/..." -o papers.csv
```

导出 XLSX（需安装 `openpyxl`）：
```bash
python journal_issue_abstract_extractor.py "https://<journal-site>/issue/..." -o papers.xlsx
```

可选参数：
```bash
--max-links 80   # 最多抓取候选文章链接
--delay 0.8      # 每篇请求间隔秒数
```
