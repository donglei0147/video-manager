# 个人视频管理工具 — FFmpeg 实现策略

| 项目 | 内容 |
|------|------|
| 版本 | v1.1 |
| 日期 | 2026-06-01 |
| 关联 | PRD `2026-06-01-video-manager-prd.md`；API `2026-06-01-video-manager-api.md` |

---

## 1. 总则

| 原则 | 说明 |
|------|------|
| 原文件保留 | v1 截取、合并均**不删除、不替换**源文件；由用户手动删除 |
| 无音频拦截 | ffprobe 检测到无音频轨时，禁止截取与合并 |
| 格式一致 | 输出容器/扩展名与源视频一致（mp4→mp4，mov→mov） |
| Seek 精度 | 单段截取使用 **`-ss` 放在 `-i` 之后**（输出侧 seek），保证切点准确 |
| 多视频合并 | 仅使用 **concat demuxer + stream copy**；编码参数不一致则**拒绝合并** |

---

## 2. 元数据校验（截取/合并前）

### 2.1 音频轨

```text
ffprobe 存在 audio stream → 允许
无 audio stream           → 拦截，错误码 NO_AUDIO_TRACK
```

扫描元数据补全时写入 `has_audio`（见数据库文档），任务提交时再次校验。

### 2.2 多视频合并 — 编码一致性

对 `video_ids` 中每个文件读取（已入库的 `video_codec`、`audio_codec`、`width`、`height`），**全部相同**才允许合并。

| 比对字段 | 说明 |
|----------|------|
| video_codec | 如 h264 |
| audio_codec | 如 aac |
| width / height | 分辨率一致 |

任一不一致 → **不发起 FFmpeg**，返回 `409 CODEC_MISMATCH`，提示用户参数不一致无法 concat copy。

> v1 **不做**转码 fallback 合并。

---

## 3. 单视频截取（单段）

### 3.1 产品行为

- **不做**一次性多段截取合并。
- 用户输入：**开始时间**（必填）、**结束时间**（可选；不填则到视频末尾）。
- 输出目录：`{源视频所在目录}/_temp/`（不存在则创建）。
- 默认文件名：与源文件 `file_name` 相同（可修改）；扩展名与源一致。
- 源视频保留，不移动、不入库替换、不进回收站。
- 输出文件**默认不自动入库**（位于 `_temp`，扫描时排除）；用户可将成品移出 `_temp` 后手动扫描入库（或 P1 提供「入库」按钮）。
- **源视频不会在 `_temp`**（扫描已跳过 `_temp` 目录）。
- `_temp` 内若输出文件已存在且同名 → **直接覆盖**（`-y`），不自动改名。

### 3.2 命令模板

设 `START`、`END` 为秒（小数允许），`END` 省略时表示到文件末尾。

**有结束时间：**

```bash
ffmpeg -y -i "{input}" -ss {START} -to {END} -c copy "{output}"
```

**无结束时间（到末尾）：**

```bash
ffmpeg -y -i "{input}" -ss {START} -c copy "{output}"
```

说明：

- `-i` 在前，`-ss` 在后 → 输出侧 seek，切点较准（解码开销更大，可接受）。
- `-c copy` 保持编码与源一致；若 copy 在切点失败（极少），任务标记 failed，**不**自动转码（v1）。

### 3.3 路径示例

```text
源：D:\Videos\a\cam01.mp4
出：D:\Videos\a\_temp\cam01.mp4   （或用户改名 cam01_clip.mp4）
```

### 3.4 校验

| 规则 | 错误 |
|------|------|
| start_sec ≥ 0 | VALIDATION_ERROR |
| end_sec 有值时 end_sec > start_sec | VALIDATION_ERROR |
| end_sec 有值时 end_sec ≤ duration_sec | VALIDATION_ERROR |
| has_audio = true | NO_AUDIO_TRACK |
| 输出路径在 _temp 下 | — |

---

## 4. 多视频合并

### 4.1 产品行为

- 用户多选并排序，指定输出文件名。
- 输出目录：**排序后第一个视频所在目录**（非 `_temp`，除非用户第一个源就在 `_temp`）。
- 合并方式：**concat demuxer + `-c copy`**。
- 编码参数预检不一致 → 拦截，不执行。
- 全部源视频保留；合并结果**默认不自动替换**源记录（新文件需用户自行扫描或 P1 入库）。

### 4.2 流程

1. 预检：音频轨、编码参数一致。
2. 生成 `filelist.txt`（UTF-8，路径转义）于临时目录。
3. 执行：

```bash
ffmpeg -y -f concat -safe 0 -i "{filelist}" -c copy "{output}"
```

4. 删除临时 `filelist.txt`。
5. 失败则源文件不变。

### 4.3 输出命名

- 默认：第一个视频的 `file_name`（API/前端预填，可改）。
- 扩展名与第一个源一致。

---

## 5. 扫描与 `_temp` 目录

- 递归扫描时**跳过**名为 `_temp` 的目录（任意层级），避免截取产物重复入库。
- 用户将成品移出 `_temp` 后，正常扫描可入库。

---

## 6. 任务类型

| job.type | 说明 |
|----------|------|
| video_clip | 单视频单段截取 |
| merge_videos | 多视频 concat demuxer 合并 |

（`clip_merge` 已废弃。）

---

## 7. 错误码（FFmpeg 相关）

| code | 说明 |
|------|------|
| NO_AUDIO_TRACK | 无音频轨 |
| CODEC_MISMATCH | 多视频编码参数不一致 |
| FFMPEG_FAILED | FFmpeg 非 0 退出 |
| OUTPUT_EXISTS | 仅用于合并输出路径已存在（可选）；截取至 _temp **始终覆盖** |

---

## 变更记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-01 | 初版：单段截取、concat demuxer 合并、原文件保留、无音频/编码拦截 |
| v1.1 | 2026-06-01 | _temp 同名覆盖；明确源文件不在 _temp |
