# 个人视频管理工具 — API 接口规格文档

| 项目 | 内容 |
|------|------|
| 文档名称 | 个人视频管理工具 API 接口规格 |
| 版本 | v1.2 |
| 日期 | 2026-06-01 |
| 状态 | 评审中 |
| Base URL | `http://localhost:8765` |
| API 前缀 | `/api` |
| 关联文档 | PRD、DB、FFmpeg 策略、工程约定 dev-guide |

---

## 1. 通用约定

### 1.1 协议与格式

- 请求/响应体：**JSON**（`Content-Type: application/json`），除文件流接口外。
- 字符编码：**UTF-8**。
- 时间字段格式：**`YYYY-MM-DD HH:MM:SS`**（本地字面量，无时区后缀）。

### 1.2 分页响应结构

列表类接口统一使用：

```json
{
  "items": [],
  "page": 1,
  "page_size": 24,
  "total": 50000,
  "total_pages": 2084
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| items | array | 当前页数据 |
| page | integer | 当前页码，从 1 开始 |
| page_size | integer | 每页条数 |
| total | integer | 符合条件的总条数 |
| total_pages | integer | 总页数 |

**分页请求参数：**

| 参数 | 类型 | 默认 | 约束 |
|------|------|------|------|
| page | integer | 1 | ≥ 1 |
| page_size | integer | 24 | 1～**100** |

### 1.3 错误响应结构

HTTP 状态码非 2xx 时，响应体：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "page_size must be between 1 and 100"
  }
}
```

### 1.4 错误码

| code | HTTP | 说明 |
|------|------|------|
| VALIDATION_ERROR | 400 | 参数校验失败 |
| NOT_FOUND | 404 | 资源不存在 |
| CONFLICT | 409 | 路径重复等冲突 |
| SCAN_IN_PROGRESS | 409 | 该文件夹正在扫描 |
| JOB_QUEUE_BUSY | 409 | FFmpeg 任务队列忙 |
| CODEC_MISMATCH | 409 | 多视频合并编码参数不一致 |
| NO_AUDIO_TRACK | 400 | 视频无音频轨，禁止截取/合并 |
| INTERNAL_ERROR | 500 | 服务端未预期错误 |
| PATH_NOT_ALLOWED | 403 | 路径不在允许的扫描目录内 |
| FILE_NOT_FOUND | 404 | 磁盘文件不存在 |

### 1.5 公共对象：VideoSummary

列表项使用（精简字段）：

```json
{
  "id": 1,
  "file_name": "clip_001.mp4",
  "ext": "mp4",
  "file_size": 524288000,
  "duration_sec": 3600.5,
  "width": 1920,
  "height": 1080,
  "record_start_at": "2024-03-15 14:30:00",
  "record_end_at": "2024-03-15 15:45:00",
  "favorite_level": 4,
  "file_mtime": "2024-06-01 10:00:00",
  "metadata_status": "ready",
  "missing": false,
  "playback_supported": true,
  "has_audio": true,
  "category": { "id": 2, "name": "家庭" },
  "tags": [{ "id": 1, "name": "旅行" }],
  "theme_background": { "id": 3, "name": "room_0001", "image_url": "/api/theme-backgrounds/3/image" },
  "stream_url": "/api/videos/1/stream"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| record_start_at | string \| null | 画面录制开始时间 |
| record_end_at | string \| null | 画面录制结束时间 |
| favorite_level | integer | 0～10 |
| metadata_status | string | pending / ready / failed |
| missing | boolean | 是否缺失 |
| playback_supported | boolean | 见 §8 |
| stream_url | string | 视频流相对路径，供 `<video src>` 与取帧 |

### 1.6 公共对象：VideoDetail

在 VideoSummary 基础上增加：

```json
{
  "id": 1,
  "scan_folder_id": 3,
  "file_path": "D:\\Videos\\a\\clip_001.mp4",
  "video_codec": "h264",
  "audio_codec": "aac",
  "indexed_at": "2024-06-01 09:00:00",
  "updated_at": "2024-06-01 10:00:00"
}
```

---

## 2. 系统（Windows）

### 2.1 选择文件夹（添加扫描目录用）

`POST /api/system/pick-folder`

**说明：** 弹出 Windows 系统文件夹选择对话框，返回用户选中的绝对路径。取消选择时返回 `204` 或 `400`（实现二选一并固定）。

**响应 200：**

```json
{
  "path": "D:\\Videos\\cam1"
}
```

**前端流程：** 设置页「添加扫描文件夹」→ 调本接口 → `POST /api/scan-folders`。

---

## 3. 扫描文件夹

### 3.1 列表扫描文件夹

`GET /api/scan-folders`

**响应 200：**

```json
{
  "items": [
    {
      "id": 1,
      "path": "D:\\Videos\\cam1",
      "enabled": true,
      "last_scan_at": "2024-06-01 10:00:00",
      "last_scan_status": "success",
      "video_count": 320,
      "created_at": "2024-05-01 08:00:00"
    }
  ]
}
```

### 3.2 添加扫描文件夹

`POST /api/scan-folders`

**请求体：**

```json
{
  "path": "D:\\Videos\\cam1"
}
```

**响应 201：** 创建的 scan_folder 对象。

**错误：** `409 CONFLICT` 路径已存在；`400` 路径无效。

### 3.3 更新扫描文件夹

`PATCH /api/scan-folders/{id}`

**请求体（均可选）：**

```json
{
  "enabled": false
}
```

### 3.4 删除扫描文件夹

`DELETE /api/scan-folders/{id}?delete_videos=false`

| 查询参数 | 类型 | 默认 | 说明 |
|----------|------|------|------|
| delete_videos | boolean | false | true 时同时删除其下 video 记录 |

**响应 204** 无 body。

### 3.5 扫描单个文件夹

`POST /api/scan-folders/{id}/scan`

**响应 202：**

```json
{
  "scan_folder_id": 1,
  "status": "scanning",
  "phase": "fast",
  "processed": 0,
  "total": 0
}
```

### 3.6 扫描全部启用文件夹

`POST /api/scan-folders/scan-all`

**响应 202：** 同上，`scan_folder_id` 可为 null 表示全局任务。

### 3.7 扫描进度

`GET /api/scan-folders/{id}/status`

**响应 200：**

```json
{
  "scan_folder_id": 1,
  "last_scan_status": "scanning",
  "phase": "metadata",
  "fast_scan": { "processed": 320, "total": 320 },
  "metadata_scan": { "processed": 120, "total": 320, "failed": 2 }
}
```

| phase | 说明 |
|-------|------|
| fast | 快速路径入库 |
| metadata | ffprobe 元数据补全 |
| idle | 无进行中的扫描 |

---

## 4. 视频

### 4.1 视频列表（分页 + 筛选）

`GET /api/videos`

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| page, page_size | integer | 分页；page_size 最大 100 |
| category_id | integer | 分类 id |
| tag_ids | string | 逗号分隔，如 `1,3,5`；**AND** 关系 |
| q | string | 文件名/路径关键词 |
| record_start_from | string | 录制开始时间下限 |
| record_start_to | string | 录制开始时间上限 |
| record_end_from | string | 录制结束时间下限 |
| record_end_to | string | 录制结束时间上限 |
| has_record_time | boolean | true=至少填了开始或结束之一；false=都未填 |
| favorite_min | integer | 最低喜爱度（含） |
| theme_background_id | integer | 按主题背景图 id 筛选 |
| include_missing | boolean | 默认 false，是否包含 missing |
| sort | string | 见下表 |

**sort 取值：**

| 值 | 说明 |
|----|------|
| file_mtime_desc | 默认，文件修改时间降序 |
| file_mtime_asc | |
| favorite_desc | 喜爱度降序 |
| favorite_asc | |
| record_start_desc | 录制开始时间降序（空值排后） |
| record_start_asc | |

**响应 200：** 分页结构，`items` 为 `VideoSummary[]`。

**筛选规则：**
- `record_start_from/to` 仅匹配 `record_start_at IS NOT NULL` 的记录。
- `record_end_from/to` 仅匹配 `record_end_at IS NOT NULL` 的记录。

### 4.2 视频详情

`GET /api/videos/{id}`

**响应 200：** `VideoDetail`

**响应 404：** 不存在。

### 4.3 更新视频标注

`PATCH /api/videos/{id}`

**请求体（字段均可选）：**

```json
{
  "category_id": 2,
  "tag_ids": [1, 3],
  "record_start_at": "2024-03-15 14:30:00",
  "record_end_at": null,
  "favorite_level": 5
}
```

| 字段 | 说明 |
|------|------|
| category_id | null 表示清除分类 |
| tag_ids | 全量替换标签列表 |
| record_*_at | null 表示清空 |
| favorite_level | 0～10 |

**响应 200：** `VideoDetail`

**校验：**
- `favorite_level` 必须在 0～10。
- 时间格式必须为 `YYYY-MM-DD HH:MM:SS`。
- 若同时提供 start/end 且均非空，建议 `record_end_at >= record_start_at`（违反时返回 400，可选实现为警告）。

### 4.4 打开文件所在目录

`POST /api/videos/{id}/open-folder`

**说明：** Windows 下调用资源管理器打开视频所在目录并选中该文件（如 `explorer /select,"{file_path}"`）。

**响应 204** 无 body。

**错误：**
- `404` 视频不存在或 `missing=true`
- `500` 系统调用失败

### 4.5 视频流（播放与首帧预览）

`GET /api/videos/{id}/stream`

**说明：**
- 支持 HTTP **Range** 请求（`206 Partial Content`）。
- 用于详情页播放与列表页首帧预览（FR-4）。
- 仅允许访问已入库且 `missing=false` 的视频；路径必须在扫描目录树下。

**请求头（可选）：**

```http
Range: bytes=0-
```

**响应：**
- `200` / `206`：`Content-Type: video/mp4` 或 `video/quicktime`（按 ext）
- `404` 文件不存在或 missing
- `403` 路径越权

**安全：** 禁止通过 id 访问未纳入扫描目录的文件（PATH_NOT_ALLOWED）。

### 4.6 从当前帧创建主题背景图

`POST /api/videos/{id}/theme-backgrounds/from-frame`

**请求体：**

```json
{
  "time_sec": 35.2,
  "name": null
}
```

| 字段 | 说明 |
|------|------|
| time_sec | 截帧时间点（秒），必填 |
| name | 可选；为空时自动生成 `room_XXXX` |

**响应 201：** `ThemeBackground` 对象；同时将当前视频关联到该背景图。

**错误：** `404` 视频不存在或文件缺失；`409` 名称重复；`400` 参数无效。

### 4.7 关联已有主题背景图

`POST /api/videos/{id}/theme-backgrounds/{background_id}/link`

**响应 200：** `VideoDetail`。若视频已有其他背景图关联则替换。

### 4.8 解除视频与主题背景图关联

`DELETE /api/videos/{id}/theme-background`

**响应 204**

---

## 5. 分类

### 5.1 列表

`GET /api/categories`

**响应 200：**

```json
{
  "items": [
    { "id": 1, "name": "家庭", "sort_order": 0, "video_count": 120 }
  ]
}
```

### 5.2 创建

`POST /api/categories`

```json
{ "name": "工作", "sort_order": 10 }
```

**响应 201**

### 5.3 更新 / 删除

`PATCH /api/categories/{id}`  
`DELETE /api/categories/{id}`

删除分类时，应用层将相关视频的 `category_id` 置空（不删视频）。

---

## 6. 标签

### 6.1 列表（支持前缀搜索）

`GET /api/tags?q=旅&limit=20`

| 参数 | 说明 |
|------|------|
| q | 名称前缀，autocomplete 用 |
| limit | 默认 20 |

**响应 200：**

```json
{
  "items": [{ "id": 1, "name": "旅行" }]
}
```

### 6.2 创建

`POST /api/tags`

```json
{ "name": "2024" }
```

### 6.3 删除

`DELETE /api/tags/{id}`

删除时清理 `video_tag` 关联（应用层）。

**响应 204**

---

## 6.5 主题背景图

### 6.5.1 对象 ThemeBackground

```json
{
  "id": 1,
  "name": "room_0001",
  "image_url": "/api/theme-backgrounds/1/image",
  "source_video_id": 12,
  "source_time_sec": 35.2,
  "width": 1920,
  "height": 1080,
  "video_count": 3,
  "created_at": "2026-06-03 17:00:00",
  "updated_at": "2026-06-03 17:00:00"
}
```

### 6.5.2 列表

`GET /api/theme-backgrounds?keyword=&page=1&page_size=24`

**响应 200：** 分页结构，`items` 为 `ThemeBackground[]`。

### 6.5.3 详情

`GET /api/theme-backgrounds/{id}`

### 6.5.4 重命名

`PATCH /api/theme-backgrounds/{id}`

```json
{ "name": "room_0002" }
```

**错误：** `409 CONFLICT` 名称已存在。

### 6.5.5 删除

`DELETE /api/theme-backgrounds/{id}`

解除所有视频关联并删除磁盘文件。**响应 204**。

### 6.5.6 图片流

`GET /api/theme-backgrounds/{id}/image`

**响应 200：** `image/jpeg`

---

## 7. 剪辑与合并任务

> FFmpeg 命令行见 `2026-06-01-video-manager-ffmpeg-strategy.md`。v1 **不删除、不替换**源文件。

### 7.1 单视频单段截取

`POST /api/jobs/video-clip`

**请求体：**

```json
{
  "video_id": 1,
  "start_sec": 10.5,
  "end_sec": 120.0,
  "output_file_name": "cam01.mp4"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_id | integer | 是 | 源视频 |
| start_sec | number | 是 | 开始时间（秒），≥ 0 |
| end_sec | number | 否 | 结束时间；**省略或 null 表示到视频末尾** |
| output_file_name | string | 否 | 输出文件名，默认与源 `file_name` 相同 |

**校验：**
- `has_audio` 必须为 true，否则 `400 NO_AUDIO_TRACK`
- `end_sec` 有值时须 `end_sec > start_sec` 且 ≤ `duration_sec`

**响应 202：**

```json
{
  "job_id": 10,
  "type": "video_clip",
  "status": "queued"
}
```

**成功后 `result` 示例：**

```json
{
  "output_path": "D:\\Videos\\a\\_temp\\cam01.mp4",
  "source_path": "D:\\Videos\\a\\cam01.mp4",
  "source_video_id": 1
}
```

- 输出目录：`{源目录}/_temp/`
- **不修改**源 `video` 记录；源文件保留
- `_temp` 内同名文件已存在时 **直接覆盖**（不报错、不自动改名）

### 7.2 多视频合并预检

`POST /api/jobs/merge-videos/preflight`

**请求体：**

```json
{
  "video_ids": [1, 5, 8]
}
```

**响应 200（通过）：**

```json
{
  "ok": true,
  "video_ids": [1, 5, 8]
}
```

**响应 409（拦截）：**

```json
{
  "error": {
    "code": "CODEC_MISMATCH",
    "message": "video_codec mismatch: h264 vs hevc",
    "details": {
      "video_codec": ["h264", "hevc"],
      "audio_codec": ["aac", "aac"],
      "width": [1920, 1920],
      "height": [1080, 1080]
    }
  }
}
```

任一源视频 `has_audio=false` 时返回 `400 NO_AUDIO_TRACK`。

### 7.3 多视频合并

`POST /api/jobs/merge-videos`

**请求体：**

```json
{
  "video_ids": [1, 5, 8],
  "output_file_name": "merged_001.mp4"
}
```

| 字段 | 说明 |
|------|------|
| video_ids | 按数组顺序合并；至少 2 个 |
| output_file_name | 可选；缺省为**排序后第一个**源视频的 `file_name` |

**提交时**自动执行与 preflight 相同校验；不一致则 `409 CODEC_MISMATCH`，不创建任务。

**响应 202：** `type`: `merge_videos`。

**成功后 `result` 示例：**

```json
{
  "output_path": "D:\\Videos\\a\\merged_001.mp4",
  "source_video_ids": [1, 5, 8]
}
```

- 输出目录：第一个源视频所在目录
- **全部源文件保留**；不自动新建/更新 `video` 记录（用户可自行扫描入库）

### 7.4 查询任务

`GET /api/jobs/{id}`

**响应 200：**

```json
{
  "id": 10,
  "type": "video_clip",
  "status": "running",
  "payload": {},
  "result": null,
  "error": null,
  "output_path": null,
  "progress": 45,
  "created_at": "2024-06-01 10:00:00",
  "started_at": "2024-06-01 10:00:01",
  "finished_at": null,
  "source_videos": [{ "id": 1, "file_name": "a.mp4" }]
}
```

| status | 说明 |
|--------|------|
| queued | 排队 |
| running | 执行中；`progress` 0～100 可选 |
| success | 成功；`result` 含新 video_id 等 |
| failed | 失败；`error` 有说明；源文件未动 |

### 7.5 任务列表

`GET /api/jobs?page=1&page_size=20&type=video_clip&status=failed`

**响应 200：** 分页，`items` 为任务摘要。

### 7.6 重试任务

`POST /api/jobs/{id}/retry`

仅 `status=failed` 可重试。**响应 202** 新 job 或复用原 job 置 queued（实现二选一并在代码注释中固定）。

---

## 8. 健康检查

`GET /api/health`

**响应 200：**

```json
{
  "status": "ok",
  "ffmpeg_available": true,
  "db_available": true
}
```

---

## 9. playback_supported 判定规则

元数据 `metadata_status=ready` 后计算，写入列表/详情响应。

| 条件 | playback_supported |
|------|-------------------|
| video_codec 为 `h264`（大小写不敏感）且 audio_codec 为 `aac` 或空（部分文件无音频轨） | true |
| video_codec 为 `hevc`/`h265`/`prores` 等 | false |
| metadata_status 非 ready | false |
| missing=true | false |

**前端行为：**
- 列表取帧：仍可对 `playback_supported=false` 尝试 stream，失败则占位图。
- 详情播放：`false` 时不自动播放，显示编码信息与提示文案。

**P1：** 不可播时提供服务端转码播放接口（不在 v1 范围）。

---

## 10. 首帧预览（前端约定）

与 FR-4 / TD-1 配合，**非独立 API**：

1. 列表渲染当前页 `VideoSummary`（≤100）。
2. 对每项创建隐藏 `<video preload="metadata" src={stream_url}>`，监听 `loadeddata` 后 `canvas` 截帧。
3. 翻页 / 筛选变更时 `abort` 或销毁上一页 video 元素。
4. `error` 或超时（建议 8s）→ 占位图。

**可选优化（v1 可不实现）：** `HEAD` stream 仅取 Content-Length，不单独建接口。

---

## 11. 接口与 FR 映射

| 接口 | FR |
|------|-----|
| scan-folders CRUD + scan | FR-1, FR-2, FR-3 |
| GET /videos | FR-4, FR-5 |
| GET /videos/{id}/stream | FR-4, FR-6 |
| PATCH /videos/{id} | FR-7 |
| POST /api/system/pick-folder | FR-1 |
| POST jobs/video-clip | FR-8, FR-11, FR-13 |
| POST jobs/merge-videos/preflight | FR-9, FR-10 |
| POST jobs/merge-videos | FR-9, FR-11, FR-13 |
| POST videos/{id}/open-folder | FR-12 |
| theme-backgrounds + videos theme APIs | FR-14 |
| categories / tags | FR-7, FR-5 |

---

## 变更记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-01 | 初版 |
| v1.1 | 2026-06-01 | video-clip 单段截取至 _temp；merge 预检；原文件保留；open-folder；无音频/编码错误码 |
| v1.2 | 2026-06-01 | pick-folder；喜爱度0-10；_temp同名覆盖；章节编号调整 |
