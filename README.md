# 个人视频管理工具

本地 Web 应用：管理 Windows 上的 mp4/mov 视频，支持扫描文件夹、增量索引、分页浏览与首帧预览。

**技术栈：** Python 3.11+ · FastAPI · SQLite · React · TypeScript · Vite · Ant Design

**当前版本范围：** 扫描、分页浏览、标注、截取、合并、删除

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

**终端 1 — 后端（开发联调端口 8766）：**

```powershell
cd D:\project\video\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8766 --reload
```

**终端 2 — 前端（开发代理）：**

```powershell
cd D:\project\video\frontend
npm run dev
```

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 浏览器访问（推荐） |
| http://127.0.0.1:8766/api/health | API 健康检查（前端代理目标） |

---

## 使用流程

1. 打开 **设置**，点击「添加扫描文件夹」→ 系统弹窗选择目录（无需手输路径）。
2. 点击「扫描」或「扫描全部（启用）」建立视频索引。
3. 在 **视频库** 分页浏览；当前页自动加载首帧预览（每页最多 100 条）。
4. 在 **详情页/列表页** 可删除视频：源文件移动到同目录 `_delete`，数据库记录真删除。
5. 多视频合并成功后，参与合并的原视频默认移动到各自目录下 `_delete`。

补充规则：

- 扫描递归跳过 `_temp` 和 `_delete` 目录。
- 截取输出到源目录 `_temp`，同名覆盖。

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
