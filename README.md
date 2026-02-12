# osm-research-skill

基于 Agent Skill 规范的 OSM 年度区域更新统计技能包。

## 结构

- `SKILL.md`：精简触发与执行说明。
- `scripts/osm_annual_pipeline.py`：自动化入口（行政区解析、bbox 校验、产物目录初始化、Mapbox bbox 图输出）。
- `references/metrics-and-methodology.md`：指标定义与统计口径。
- `references/collection-architecture.md`：分层采集、重试与断点续跑。
- `references/mapbox-static-overlay.md`：bbox 叠加图细节。
- `references/summary-schema.md`：`summary.json` 建议结构。

## 快速开始

```bash
python3 scripts/osm_annual_pipeline.py \
  --region-query "Macau" \
  --year 2025 \
  --mapbox-token-env MAPBOX_ACCESS_TOKEN
```
