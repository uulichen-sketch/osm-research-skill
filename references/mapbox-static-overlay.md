# Mapbox Static Overlay

## 目录

- [1. 目标](#1-目标)
- [2. bbox 矩形 GeoJSON](#2-bbox-矩形-geojson)
- [3. 请求格式](#3-请求格式)

## 1. 目标

生成 `figures/bbox_map.png`：
- 视图以 bbox 自适应；
- 叠加 bbox 红色边框；
- 产物本地可直接入报告。

## 2. bbox 矩形 GeoJSON

闭合 ring：
`(minLon,minLat) → (maxLon,minLat) → (maxLon,maxLat) → (minLon,maxLat) → (minLon,minLat)`。

Overlay 建议：`geojson({ENCODED_GEOJSON})`。

## 3. 请求格式

```text
https://api.mapbox.com/styles/v1/{style}/static/{overlay}/[{minLon},{minLat},{maxLon},{maxLat}]/{width}x{height}?access_token=...
```

注意事项：
- token 从环境变量读取；
- overlay 需 URL encode；
- URL 长度上限通常 8192，bbox 矩形通常安全。
