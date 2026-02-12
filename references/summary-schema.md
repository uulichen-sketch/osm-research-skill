# summary.json Schema (Recommended)

## 目录

- [meta](#meta)
- [changesets](#changesets)
- [contributors](#contributors)
- [features](#features)
- [roads](#roads)
- [quality](#quality)

## meta

- `region_query`
- `chosen_osm_object`
- `boundary_source`
- `bbox`
- `polygon_hash`
- `year`, `t_start`, `t_end`, `granularity`

## changesets

- `CS_total`, `CHG_total`
- `monthly[]`
- `created_by_topk` (optional)
- `discussion_stats` (optional)

## contributors

- `U_total`, `AU_10cs`, `AU_500chg`
- `topk_users_by_chg`

## features

- `FEAT_EDIT_total`
- `FEAT_EDIT_BY_TAG_total`
- `UNIQUE_FEAT_total` (optional)

## roads

- `ERL_raw_total`, `ERL_unique_total`
- `monthly[]`
- `missing_nodes_rate`, `affected_ways_count`
- `method_note`

## quality

- `truncation_windows`
- `bbox_cross_border_risk_note`
- `api_errors`, `retries`, `partial_failures`
