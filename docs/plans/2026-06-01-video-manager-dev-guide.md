# 个人视频管理工具 — 工程约定（Dev Guide）

| 项目 | 内容 |
|------|------|
| 文档名称 | 个人视频管理工具 工程约定 |
| 版本 | v1.0 |
| 日期 | 2026-06-01 |
| 状态 | 开发与 AI 实现权威补充 |
| 权威文档顺序 | ① PRD → ② DB → ③ API → ④ FFmpeg 策略 → **⑤ 本文** |
| 仅备份、禁止实现参考 | `2026-06-01-video-manager-design.md` |

> 本文与 PRD/API/DB 冲突时，以**本文 §12 已确认条款**为准。

---

## 1. 技术栈与版本

| 组件 | 选型 | 版本建议 |
|------|------|----------|
| 语言 | Python | 3.11+ |
| 后端 | FastAPI | 0.110+ |
| ORM | SQLAlchemy 2.x | — |
| 数据库 | SQLite | 3 |
| 前端 | React + TypeScript | 18+ |
| 构建 | Vite | 5+ |
| UI | Ant Design | 5.x |
| 媒体 | FFmpeg / ffprobe | 系统 PATH 可用 |
| 运行环境 | Windows | 10/11 64 位 |

---

## 2. 仓库目录结构

```text
video-manager/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db/
│   │   ├── api/
│   │   ├── services/
│   │   ├── jobs/
│   │   └── schemas/
│   ├── scripts/
│   │   └── init_db.sql
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── pages/
│   │   ├── components/
│   │   └── hooks/
│   ├── package.json
│   └── vite.config.ts
├── data/                 # gitignore
│   └── app.db
├── docs/plans/
└── README.md
```

---

## 3. 配置项

| 配置 | 默认 | 说明 |
|------|------|------|
| `HOST` | `127.0.0.1` | 仅本机 |
| `PORT` | `8765` | API 端口 |
| `DATABASE_URL` | `sqlite:///./data/app.db` | |
| `FFMPEG_PATH` | `ffmpeg` | |
| `FFPROBE_PATH` | `ffprobe` | |
| `JOB_CONCURRENCY` | `1` | FFmpeg 任务并发 |
| `CORS_ORIGINS` | `http://localhost:5173` | Vite 开发 |
| `ASSETS_DIR` | `./data/assets/theme-backgrounds` | 主题背景图存储目录 |

---

## 4. 启动方式

**开发：**

```text
终端1: cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
终端2: cd frontend && npm run dev
浏览器: http://localhost:5173
```

**健康检查：** `GET http://127.0.0.1:8765/api/health`

---

## 5. 文档优先级

1. `2026-06-01-video-manager-prd.md`
2. `2026-06-01-video-manager-database.md`
3. `2026-06-01-video-manager-api.md`
4. `2026-06-01-video-manager-ffmpeg-strategy.md`
5. **本文**

**禁止**以 `2026-06-01-video-manager-design.md` 为实现依据（仅历史备份）。

---

## 6. 数据库约定

- 不使用外键；完整性由应用层维护。
- 时间：`YYYY-MM-DD HH:MM:SS`，不做 UTC 转换。
- 启动：`PRAGMA journal_mode=WAL;`
- 建表：见 `backend/scripts/init_db.sql` 或迁移，与 DB 文档一致。

---

## 7. API 实现约定

- 前缀 `/api`；统一错误体 `{ "error": { "code", "message" } }`。
- 分页：`page` 从 1 起，`page_size` 最大 **100**。
- 视频流：Range；路径须在已配置 `scan_folder` 子树内。
- FFmpeg 任务：**单并发**；进程重启后将 `running` 任务标为 `failed`。

---

## 8. 扫描文件夹：弹窗选择（Windows）

- 添加扫描目录：**系统文件夹选择对话框**，不需拖拽、不需手输（路径只读展示）。
- 实现：`POST /api/system/pick-folder` 调 Windows 原生目录选择，返回绝对路径后 `POST /api/scan-folders`。
- 扫描：递归 mp4/mov；**跳过**任意层级目录名 `_temp`、`_delete`。

---

## 9. 前端约定

| 模块 | 约定 |
|------|------|
| 视频库 | 分页 + 筛选；首帧仅当前页（≤100） |
| 分类管理 | 分类 CRUD |
| 主题背景图 | 列表、搜索、重命名、删除；点击跳转视频库筛选 |
| 详情 | 播放、标注、主题背景图截帧/关联、打开所在目录、截取入口 |
| 删除 | 删除视频时将源文件移动到源目录 `_delete`，并从库中删除记录 |
| 截取 | 开始必填、结束可空；默认输出名=源文件名 |
| 合并 | preflight → 提交；默认文件名=**排序后第一个**源文件名 |
| 喜爱度 | **0～10**（0=未设置） |

---

## 10. FFmpeg / `_temp`

- 截取输出：`{源目录}/_temp/{文件名}`；**源文件不会在 `_temp`**（扫描已排除）。
- `_temp` 内**同名输出直接覆盖**，不自动改名。
- 合并输出：第一个源视频所在目录（非 `_temp`）；编码不一致拦截。
- 合并成功后：原视频默认移动到各自源目录下的 `_delete` 文件夹；若不存在则自动创建。
- 详见 `2026-06-01-video-manager-ffmpeg-strategy.md`。

---

## 11. 合并默认文件名

- 默认 = 排序后**第一个**视频的 `file_name`（含扩展名）。
- 用户提交前可修改；**不**自动加日期等后缀。

---

## 12. 删除行为（真删除 + 移入 `_delete`）

- 删除视频为“移入 `_delete`”语义：将源文件移动到其所在目录下 `_delete/{原文件名}`。
- 若 `_delete` 不存在，自动创建；若目标同名已存在，直接覆盖。
- 删除后从数据库中删除该视频记录（真删除），不再保留 `missing=1` 记录。
- 扫描任务递归跳过 `_delete`，避免被再次纳入视频库。

---

## 13. 产品确认条款（权威）

| 条款 | 约定 |
|------|------|
| design.md | 仅备份，禁止实现参考 |
| 扫描目录 | Windows 弹窗选文件夹 |
| 喜爱度 | **0～10**，0=未设置 |
| 合并默认名 | 第一个源文件名，手工可改 |
| `_temp` 覆盖 | 同名则覆盖；源不在 `_temp` |
| 合并后原视频 | 默认移入源目录 `_delete` |
| 删除语义 | 删除即移入源目录 `_delete`，并从库中真删除记录 |
| 扫描排除 | 递归跳过 `_temp`、`_delete` |

---

## 14. AI 开发提示（可复制）

```text
权威：prd.md、database.md、api.md、ffmpeg-strategy.md、dev-guide.md
禁止：design.md

顺序：PRD Phase 1→5
硬约束：弹窗选扫描目录；喜爱度0-10；合并默认名=排序后第一个源文件名；
截取至源目录/_temp/同名覆盖；扫描跳过_temp与_delete；合并后原视频移入源目录/_delete；
删除即移入源目录/_delete并从库中真删除记录；合并编码不一致拦截。
```

---

## 变更记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-01 | 初版工程约定 |
