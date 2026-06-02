# Phase 5 全量 AC 回归清单

## 使用方式

- 启动后端：`cd backend && .\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8765`
- 按顺序执行：
  - `.\.venv\Scripts\python.exe scripts\phase1_check.py`
  - `.\.venv\Scripts\python.exe scripts\phase2_check.py`
  - `.\.venv\Scripts\python.exe scripts\phase3_check.py`
  - `.\.venv\Scripts\python.exe scripts\phase4_check.py`
  - `.\.venv\Scripts\python.exe scripts\phase5_check.py`

## AC 覆盖映射

- **Phase 1（FR-1~FR-4）**
  - 扫描文件夹增删改查、重复路径拦截
  - 递归扫描与 `_temp` 跳过
  - 分页列表与基础返回字段
- **Phase 2（FR-5~FR-7, FR-13）**
  - 分类/标签/录制时间/喜爱度保存与筛选排序
  - 播放流 Range 行为
  - 无音频拦截
- **Phase 3（FR-8）**
  - 单段截取到 `{源目录}/_temp`
  - 同名覆盖
  - 原文件保留
- **Phase 4（FR-9~FR-10）**
  - `merge-videos/preflight`
  - `merge-videos` + concat demuxer
  - `CODEC_MISMATCH` 拦截
- **Phase 5（联调补齐）**
  - 增量扫描后标注保留
  - `open-folder` 接口可用
  - 任务列表筛选、失败任务重试

## 前端手工回归要点（Settings）

- 扫描文件夹页：
  - 添加/删除/启用/停用/单扫/全扫
  - 扫描状态与错误提示可见
- 任务列表：
  - 可按类型、状态筛选
  - 失败任务点击“重试”后状态回到 `queued`
- 视频详情：
  - “打开文件所在目录”可用（missing 时禁用）
