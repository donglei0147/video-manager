import { DeleteOutlined } from "@ant-design/icons";
import { Button, Card, Checkbox, Popconfirm, Space, Tag, Typography } from "antd";
import { Link } from "react-router-dom";
import type { VideoSummary } from "../api/types";
import VideoThumbnail from "./VideoThumbnail";

const { Text, Paragraph } = Typography;

function formatDuration(sec: number | null) {
  if (sec == null) return "—";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

interface Props {
  video: VideoSummary;
  loadThumbnail: boolean;
  viewMode: "grid" | "list";
  selectable?: boolean;
  selected?: boolean;
  onSelectChange?: (videoId: number, checked: boolean) => void;
  onDelete?: (videoId: number) => Promise<void> | void;
}

export default function VideoCard({
  video,
  loadThumbnail,
  viewMode,
  selectable = false,
  selected = false,
  onSelectChange,
  onDelete,
}: Props) {
  const resolution =
    video.width && video.height ? `${video.width}×${video.height}` : "—";
  const metaLabel =
    video.metadata_status === "pending"
      ? "解析中"
      : video.metadata_status === "failed"
        ? "解析失败"
        : null;

  const thumb = (
    <VideoThumbnail
      streamUrl={video.stream_url}
      enabled={loadThumbnail && !video.missing}
      alt={video.file_name}
    />
  );

  const gridMetaTags = (
    <>
      {video.category && <Tag>{video.category.name}</Tag>}
      {video.tags.slice(0, 2).map((t) => (
        <Tag key={t.id} color="blue">
          {t.name}
        </Tag>
      ))}
      {video.tags.length > 2 && <Tag>+{video.tags.length - 2}</Tag>}
    </>
  );

  const listInfo = (
    <>
      <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 4 }}>
        <Text strong>{video.file_name}</Text>
      </Paragraph>
      <Space direction="vertical" size={2} style={{ width: "100%" }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          时长 {formatDuration(video.duration_sec)} · {resolution} · {formatSize(video.file_size)}
        </Text>
        {(video.record_start_at || video.record_end_at) && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            录制 {video.record_start_at ?? "—"} ~ {video.record_end_at ?? "—"}
          </Text>
        )}
        <Text type="secondary" style={{ fontSize: 12 }}>
          喜爱度 {video.favorite_level}
        </Text>
        <Space size={[4, 4]} wrap>
          {gridMetaTags}
          {metaLabel && <Tag color="orange">{metaLabel}</Tag>}
          {!video.has_audio && <Tag color="volcano">无音频</Tag>}
          {video.missing && <Tag color="red">缺失</Tag>}
        </Space>
        <Link to={`/videos/${video.id}`} style={{ fontSize: 12 }}>
          详情 / 播放
        </Link>
        {onDelete && (
          <Popconfirm
            title="删除视频"
            description="将源文件移入 _delete，并从库中删除记录。"
            okText="确认删除"
            cancelText="取消"
            onConfirm={() => onDelete(video.id)}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        )}
      </Space>
    </>
  );

  if (viewMode === "list") {
    return (
      <Card className={`video-card video-card-list ${selected ? "video-card-selected" : ""}`} size="small">
        <div className="video-card-list-inner">
          <div className="thumb-wrap-list">{thumb}</div>
          <div className="video-card-info">{listInfo}</div>
          {selectable && (
            <Checkbox
              checked={selected}
              onChange={(e) => onSelectChange?.(video.id, e.target.checked)}
            />
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card
      className={`video-card video-card-grid ${selected ? "video-card-selected" : ""}`}
      cover={
        <div className="thumb-wrap">
          {thumb}
          <div className="video-card-overlay">
            <div className="video-card-overlay-top">
              <Space size={4} wrap>
                {metaLabel && <Tag color="orange">{metaLabel}</Tag>}
                {!video.has_audio && <Tag color="volcano">无音频</Tag>}
                {video.missing && <Tag color="red">缺失</Tag>}
              </Space>
              {selectable && (
                <Checkbox
                  checked={selected}
                  onChange={(e) => onSelectChange?.(video.id, e.target.checked)}
                  onClick={(e) => e.stopPropagation()}
                />
              )}
            </div>
            <div className="video-card-overlay-bottom">
              <Paragraph ellipsis={{ rows: 1 }} style={{ marginBottom: 6 }}>
                <Text strong style={{ color: "#fff" }}>
                  {video.file_name}
                </Text>
              </Paragraph>
              <Text className="video-card-overlay-meta">
                {formatDuration(video.duration_sec)} · {resolution} · {formatSize(video.file_size)}
              </Text>
              <Text className="video-card-overlay-meta">喜爱度 {video.favorite_level}</Text>
              <div className="video-card-overlay-tags">{gridMetaTags}</div>
            </div>
          </div>
        </div>
      }
      size="small"
    >
      <Space size={8}>
        <Link to={`/videos/${video.id}`} style={{ fontSize: 12 }}>
          详情 / 播放
        </Link>
        {onDelete && (
          <Popconfirm
            title="删除视频"
            description="将源文件移入 _delete，并从库中删除记录。"
            okText="确认删除"
            cancelText="取消"
            onConfirm={() => onDelete(video.id)}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        )}
      </Space>
    </Card>
  );
}
