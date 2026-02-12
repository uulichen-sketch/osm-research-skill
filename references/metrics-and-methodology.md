# Metrics and Methodology

## 目录

- [1. Changeset / 社区贡献指标](#1-changeset--社区贡献指标)
- [2. 要素更新指标（基于 OsmChange）](#2-要素更新指标基于-osmchange)
- [3. 道路长度指标口径](#3-道路长度指标口径)
- [4. 局限披露模板](#4-局限披露模板)

## 1. Changeset / 社区贡献指标

1) **CS（Changeset Count）**
- 定义：统计窗内（建议 UTC）且 bbox 命中的 changeset 数。

2) **CHG（Total changes_count）**
- 定义：命中 changeset 的 `changes_count` 求和。
- 注意：不是“独立要素数”。

3) **U（Contributors）**
- 定义：去重 uid 数。

4) **AU（活跃贡献者）**
- `AU_10cs`：年内 changeset ≥ 10
- `AU_500chg`：年内 changes_count ≥ 500

5) **EDITOR（可选）**
- changeset tag `created_by` 分布。

6) **DISC（可选）**
- changeset discussion 评论统计。

## 2. 要素更新指标（基于 OsmChange）

- `FEAT_EDIT`：N/W/R × create/modify/delete。
- `FEAT_EDIT_BY_TAG` 主题分类建议：
  - roads：`way + highway=*`
  - buildings：`building=*`
  - pois：`amenity=*` / `shop=*` / `tourism=*`
  - landuse：`landuse=*`
  - water：`waterway=*` / `natural=water`
  - boundaries：`boundary=*`
- `UNIQUE_FEAT`（可选）：按 `(type,id)` 去重。

## 3. 道路长度指标口径

### ERL（推荐默认）

- `ERL_raw`：create+modify 的 highway ways 长度总和（不去重）。
- `ERL_unique`：按 way_id 去重后长度总和。

### NRL（可选）

- create 中 highway ways 长度和。

### ΔRL（默认不做）

- modify 的新旧长度差值和，需 history/version，成本高。

## 4. 局限披露模板

- bbox 命中不等于要素都在行政区内（可能跨界）。
- `changes_count` 表示版本变更次数，不等于独立对象数。
- 道路长度受 nodes 缺失影响，应披露 `missing_nodes_rate`。
