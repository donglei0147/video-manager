# 个人视频管理工具

本地 Web 应用：管理 Windows 上的 mp4/mov 视频，支持扫描文件夹、增量索引、分页浏览与首帧预览。

**技术栈：** Python 3.11+ · FastAPI · SQLite · React · TypeScript · Vite · Ant Design

**当前版本范围：** PRD Phase 1（扫描文件夹、快速扫描、分页列表、首帧预览）

---

## 环境要求

- Windows 10/11
- Python 3.11+
- Node.js 18+
- FFmpeg / ffprobe 已加入系统 PATH（健康检查会检测，Phase 1 扫描不调用 ffprobe）

---

## 安装

### 后端

```powershell
cd D:\project\video\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 前端

```powershell
cd D:\project\video\frontend
npm install
```

数据库文件首次启动时自动创建于 `data/app.db`。

---

## 启动

**终端 1 — 后端（端口 8765）：**

```powershell
cd D:\project\video\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

**终端 2 — 前端（开发代理）：**

```powershell
cd D:\project\video\frontend
npm run dev
```

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 浏览器访问（推荐） |
| http://127.0.0.1:8765/api/health | API 健康检查 |

---

## 使用流程

1. 打开 **设置**，点击「添加扫描文件夹」→ 系统弹窗选择目录（无需手输路径）。
2. 点击「扫描」或「扫描全部（启用）」建立视频索引。
3. 在 **视频库** 分页浏览；当前页自动加载首帧预览（每页最多 100 条）。

---

## 项目结构

```text
backend/app/     FastAPI 应用
backend/scripts/ init_db.sql
frontend/src/    React 前端
data/            SQLite（gitignore）
docs/plans/      权威设计文档
```

---

## 文档

实现依据（按顺序）：

1. `docs/plans/2026-06-01-video-manager-prd.md`
2. `docs/plans/2026-06-01-video-manager-database.md`
3. `docs/plans/2026-06-01-video-manager-api.md`
4. `docs/plans/2026-06-01-video-manager-ffmpeg-strategy.md`
5. `docs/plans/2026-06-01-video-manager-dev-guide.md`

勿参考已过期的 `design.md`。

---

## 其他脚本

仓库根目录另有人脸裁剪工具 `face_extract.py`，与本应用无关。
