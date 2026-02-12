# Collection Architecture

## 目录

- [1. 分层采集](#1-分层采集)
- [2. 断点续跑策略](#2-断点续跑策略)
- [3. 速率限制与重试](#3-速率限制与重试)

## 1. 分层采集

### 层 0：capabilities 快照
- 请求 `GET {osm_api_base}/api/capabilities`。
- 记录服务限制，落盘 `meta/capabilities.xml`。

### 层 1：changesets 列表
- 按月/周拉取 changesets。
- 当窗口命中 `limit` 上限（常见 100）时自动二分窗口，直到每窗 < limit。
- 落盘 `raw/changesets.csv`。

### 层 2：changeset download
- 对每个 changeset 拉 `.../changeset/{id}/download`。
- 落盘 `raw/changeset_download/{id}.osc.xml(.gz)`。

### 层 3：道路长度
- 提取 highway ways 的 node refs。
- 批量请求 nodes multi-fetch。
- 使用统一算法（WGS84 geodesic 或球面近似）计算长度并记录算法说明。

## 2. 断点续跑策略

- 已存在的时间窗结果不重复抓取。
- 已存在的 `changeset_download` 文件跳过。
- node 坐标缓存（SQLite/KV）避免重复请求。

## 3. 速率限制与重试

- 429/5xx：指数退避。
- 分层并发控制：
  - 层 1 低并发；
  - 层 2 中等并发；
  - 层 3 批量请求并发。
