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


### 在 Colab / Jupyter 中使用
某些笔记本环境会自动注入 `-f` 参数。脚本已兼容该场景（会忽略未知参数），可直接运行：
```bash
python journal_issue_abstract_extractor.py "https://<journal-site>/issue/..." -o papers.csv
```


如果出现 `MissingSchema`（例如把 `kernel-xxxx.json` 误当成 URL），请确认第一个参数是真实期刊链接，且以 `http://` 或 `https://` 开头。


在 Colab/Jupyter 里如果未传入真实 `issue_url`，脚本现在会打印帮助并正常退出（不会再抛出 `SystemExit: 2` 参数错误）。
