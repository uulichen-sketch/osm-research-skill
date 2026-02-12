---
name: osm-annual-region-update
description: Compute annual OpenStreetMap update statistics for an administrative region (changesets, contributors, feature edits, road metrics), generate a bbox overlay static map via Mapbox, and persist full local outputs.
---

# OSM 区域年度更新统计 Skill

用于“行政区 + 年度”的 OSM 更新统计与落盘交付（示例：Macau 2025）。

## 触发场景

- 用户要求某地区某年度 OSM 活跃度/贡献者/要素更新统计。
- 用户要求可复现的数据采集流水线与本地文件产物。
- 用户要求输出 bbox 叠加静态地图（Mapbox Static Images API）。

## 最小输入

- `region_query`（如 `Macau`）
- `year`（如 `2025`）
- `MAPBOX_ACCESS_TOKEN`（用于地图输出）

可选参数见脚本 `--help`（timezone, granularity, API base, image size 等）。

## 推荐执行流程（先脚本）

```bash
python3 scripts/osm_annual_pipeline.py \
  --region-query "Macau" \
  --year 2025 \
  --mapbox-token-env MAPBOX_ACCESS_TOKEN
```

脚本会自动：

1. 解析行政区候选并选择目标对象（Nominatim search + lookup）。
2. 获取 polygon 与 bbox，并做 bbox 一致性校验。
3. 生成标准目录结构与 `meta/region.json`、`stats/summary.json`、`stats/monthly.csv`、`logs/run.log`。
4. 输出 bbox 叠加地图 `figures/bbox_map.png`。
5. 预创建 changeset/raw 目录，为后续全量采集留接口。

## 深入内容按需加载

- 指标定义与口径：`references/metrics-and-methodology.md`
- 采集分层/容错/断点续跑：`references/collection-architecture.md`
- Mapbox bbox 叠加实现细节：`references/mapbox-static-overlay.md`
- `summary.json` 建议 schema：`references/summary-schema.md`

## 产出要求

- 所有输出必须落盘到 `outputs/<region>/<year>/...`。
- 报告中必须披露局限：bbox 跨界、changes_count 含义、节点缺失导致道路长度低估等。
