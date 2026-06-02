import {
  DeleteOutlined,
  FolderAddOutlined,
  RedoOutlined,
  ScanOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import {
  Button,
  Card,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { listJobs, retryJob } from "../api/jobs";
import {
  createScanFolder,
  deleteScanFolder,
  getScanStatus,
  listScanFolders,
  pickFolder,
  scanAllFolders,
  resyncMetadata,
  scanFolder,
  updateScanFolder,
} from "../api/scanFolders";
import type { JobSummary, ScanFolder } from "../api/types";

const { Title, Text } = Typography;

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  idle: { color: "default", label: "未扫描" },
  scanning: { color: "processing", label: "扫描中" },
  success: { color: "success", label: "成功" },
  failed: { color: "error", label: "失败" },
};

export default function SettingsPage() {
  const [folders, setFolders] = useState<ScanFolder[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [jobLoading, setJobLoading] = useState(false);
  const [jobType, setJobType] = useState<string | undefined>(undefined);
  const [jobStatus, setJobStatus] = useState<string | undefined>(undefined);
  const pollRef = useRef<number | null>(null);
  const jobPollRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listScanFolders();
      setFolders(data.items);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadJobs = useCallback(async () => {
    setJobLoading(true);
    try {
      const data = await listJobs({ page: 1, page_size: 30, type: jobType, status: jobStatus });
      setJobs(data.items);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "任务加载失败");
    } finally {
      setJobLoading(false);
    }
  }, [jobStatus, jobType]);

  useEffect(() => {
    void load();
    void loadJobs();
    jobPollRef.current = window.setInterval(() => {
      void loadJobs();
    }, 2000);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
      if (jobPollRef.current) window.clearInterval(jobPollRef.current);
    };
  }, [load, loadJobs]);

  const startPoll = (folderId: number) => {
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      try {
        const st = await getScanStatus(folderId);
        await Promise.all([load(), loadJobs()]);
        if (st.last_scan_status !== "scanning") {
          if (pollRef.current) window.clearInterval(pollRef.current);
          pollRef.current = null;
          if (st.last_scan_status === "failed") {
            message.error(st.last_scan_error ?? "扫描失败，请查看列表中的失败原因");
          } else {
            message.success("扫描完成，请刷新视频库查看最新列表");
          }
        }
      } catch {
        /* ignore poll errors */
      }
    }, 800);
  };

  const handleAdd = async () => {
    try {
      const picked = await pickFolder();
      if (!picked?.path) {
        message.info("已取消选择");
        return;
      }
      await createScanFolder(picked.path);
      message.success("已添加扫描文件夹");
      await load();
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else message.error("添加失败");
    }
  };

  const handleDelete = (folder: ScanFolder) => {
    Modal.confirm({
      title: "删除扫描文件夹",
      content: (
        <div>
          <p>路径：{folder.path}</p>
          <p>是否同时删除该文件夹下的所有视频记录？</p>
        </div>
      ),
      okText: "删除记录并移除文件夹",
      cancelText: "仅移除文件夹配置",
      onOk: async () => {
        await deleteScanFolder(folder.id, true);
        message.success("已删除文件夹及其视频记录");
        await load();
      },
      footer: (_, { OkBtn, CancelBtn }) => (
        <>
          <CancelBtn />
          <Button
            onClick={async () => {
              Modal.destroyAll();
              await deleteScanFolder(folder.id, false);
              message.success("已移除文件夹配置，视频记录已保留");
              await load();
            }}
          >
            保留视频记录
          </Button>
          <OkBtn />
        </>
      ),
    });
  };

  const handleScan = async (id: number) => {
    try {
      await scanFolder(id);
      message.info("扫描已开始");
      startPoll(id);
      await load();
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
    }
  };

  const handleResyncMetadata = async (id: number) => {
    try {
      await resyncMetadata(id);
      message.info("正在补全元数据…");
      startPoll(id);
      await Promise.all([load(), loadJobs()]);
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
    }
  };

  const handleScanAll = async () => {
    try {
      await scanAllFolders();
      message.info("已开始扫描全部启用文件夹");
      await Promise.all([load(), loadJobs()]);
      const enabled = folders.filter((f) => f.enabled);
      if (enabled.length === 1) startPoll(enabled[0].id);
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
    }
  };

  const columns: ColumnsType<ScanFolder> = [
    {
      title: "路径",
      dataIndex: "path",
      ellipsis: true,
      render: (path: string) => <Text copyable>{path}</Text>,
    },
    {
      title: "启用",
      dataIndex: "enabled",
      width: 80,
      render: (enabled: boolean, row) => (
        <Switch
          checked={enabled}
          onChange={async (v) => {
            await updateScanFolder(row.id, v);
            await load();
          }}
        />
      ),
    },
    {
      title: "状态",
      dataIndex: "last_scan_status",
      width: 280,
      render: (s: string, row: ScanFolder) => {
        const m = STATUS_MAP[s] ?? { color: "default", label: s };
        const tag = <Tag color={m.color}>{m.label}</Tag>;
        if (s === "failed" && row.last_scan_error) {
          return (
            <Tooltip title={row.last_scan_error} placement="topLeft">
              <div style={{ cursor: "help" }}>
                {tag}
                <Text type="danger" style={{ display: "block", fontSize: 12, marginTop: 4 }}>
                  {row.last_scan_error.length > 80
                    ? `${row.last_scan_error.slice(0, 80)}…`
                    : row.last_scan_error}
                </Text>
              </div>
            </Tooltip>
          );
        }
        if (s === "scanning") {
          return tag;
        }
        return tag;
      },
    },
    {
      title: "视频数",
      dataIndex: "video_count",
      width: 80,
    },
    {
      title: "上次扫描",
      dataIndex: "last_scan_at",
      width: 170,
      render: (t: string | null) => t ?? "—",
    },
    {
      title: "操作",
      width: 280,
      render: (_, row) => (
        <Space wrap>
          <Button
            size="small"
            icon={<ScanOutlined />}
            disabled={!row.enabled || row.last_scan_status === "scanning"}
            onClick={() => handleScan(row.id)}
          >
            扫描
          </Button>
          <Button
            size="small"
            disabled={!row.enabled || row.last_scan_status === "scanning" || row.video_count === 0}
            onClick={() => handleResyncMetadata(row.id)}
          >
            补全元数据
          </Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(row)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const jobColumns: ColumnsType<JobSummary> = [
    {
      title: "ID",
      dataIndex: "id",
      width: 72,
    },
    {
      title: "类型",
      dataIndex: "type",
      width: 120,
      render: (t: string) => {
        if (t === "video_clip") return "单段截取";
        if (t === "merge_videos") return "多视频合并";
        return t;
      },
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 110,
      render: (s: string) => {
        const color =
          s === "success" ? "success" : s === "failed" ? "error" : s === "running" ? "processing" : "default";
        return <Tag color={color}>{s}</Tag>;
      },
    },
    {
      title: "源视频",
      dataIndex: "source_videos",
      ellipsis: true,
      render: (items: { file_name: string }[]) => items.map((i) => i.file_name).join("，") || "—",
    },
    {
      title: "错误",
      dataIndex: "error",
      ellipsis: true,
      render: (e: string | null) => (e ? <Text type="danger">{e}</Text> : "—"),
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 170,
    },
    {
      title: "操作",
      width: 96,
      render: (_, row) => (
        <Button
          size="small"
          icon={<RedoOutlined />}
          disabled={row.status !== "failed"}
          onClick={async () => {
            try {
              await retryJob(row.id);
              message.success("已重试任务");
              await loadJobs();
            } catch (e) {
              message.error(e instanceof Error ? e.message : "重试失败");
            }
          }}
        >
          重试
        </Button>
      ),
    },
  ];

  return (
    <div className="page settings-page">
      <div className="page-header">
        <Title level={3} style={{ margin: 0 }}>
          设置 · 扫描文件夹
        </Title>
        <Space>
          <Button type="primary" icon={<FolderAddOutlined />} onClick={handleAdd}>
            添加扫描文件夹
          </Button>
          <Button icon={<SyncOutlined />} onClick={handleScanAll}>
            扫描全部（启用）
          </Button>
          <Button icon={<SyncOutlined />} onClick={load} loading={loading}>
            刷新
          </Button>
        </Space>
      </div>
      <Card size="small" title="扫描文件夹">
        <Table
          rowKey="id"
          columns={columns}
          dataSource={folders}
          loading={loading}
          pagination={false}
          size="middle"
        />
      </Card>
      <Card
        size="small"
        title="任务列表"
        style={{ marginTop: 16 }}
        extra={
          <Space>
            <Select
              allowClear
              placeholder="任务类型"
              style={{ width: 140 }}
              value={jobType}
              onChange={setJobType}
              options={[
                { value: "video_clip", label: "单段截取" },
                { value: "merge_videos", label: "多视频合并" },
              ]}
            />
            <Select
              allowClear
              placeholder="任务状态"
              style={{ width: 120 }}
              value={jobStatus}
              onChange={setJobStatus}
              options={[
                { value: "queued", label: "queued" },
                { value: "running", label: "running" },
                { value: "success", label: "success" },
                { value: "failed", label: "failed" },
              ]}
            />
            <Button onClick={loadJobs} loading={jobLoading}>
              刷新任务
            </Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          columns={jobColumns}
          dataSource={jobs}
          loading={jobLoading}
          pagination={false}
          size="small"
        />
      </Card>
      <Text type="secondary" style={{ display: "block", marginTop: 16 }}>
        添加时请使用系统文件夹选择对话框，无需手输路径。扫描将递归发现 mp4/mov，并跳过名为 _temp 的目录。
      </Text>
    </div>
  );
}
