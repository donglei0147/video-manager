import { ArrowLeftOutlined, DeleteOutlined, FolderOpenOutlined, PictureOutlined } from "@ant-design/icons";
import {
  Button,
  DatePicker,
  Drawer,
  Input,
  InputNumber,
  Row,
  Col,
  Space,
  Select,
  Tag,
  Typography,
  Modal,
  message,
} from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { listCategories, type Category } from "../api/categories";
import { ApiError } from "../api/client";
import { getOrCreateTag, listTags } from "../api/tags";
import {
  createThemeBackgroundFromFrame,
  linkThemeBackground,
  listThemeBackgrounds,
  type ThemeBackground,
} from "../api/themeBackgrounds";
import {
  createVideoClip,
  deleteVideo,
  getVideo,
  openVideoFolder,
  updateVideo,
  type VideoDetail,
} from "../api/videos";
import FavoriteStars from "../components/FavoriteStars";

const { Title, Text, Paragraph } = Typography;
const DATETIME_FMT = "YYYY-MM-DD HH:mm:ss";

function toDayjs(s: string | null): Dayjs | null {
  if (!s) return null;
  return dayjs(s, DATETIME_FMT);
}

function fromDayjs(d: Dayjs | null): string | null {
  return d ? d.format(DATETIME_FMT) : null;
}

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const videoId = Number(id);

  const [video, setVideo] = useState<VideoDetail | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tagOptions, setTagOptions] = useState<{ value: string; id: number }[]>([]);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [tagLabels, setTagLabels] = useState<Record<number, string>>({});
  const [tagInput, setTagInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [clipStart, setClipStart] = useState<number | null>(null);
  const [clipEnd, setClipEnd] = useState<number | null>(null);
  const [clipName, setClipName] = useState("");
  const [clipping, setClipping] = useState(false);
  const [clipOpen, setClipOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [themeModalOpen, setThemeModalOpen] = useState(false);
  const [themeName, setThemeName] = useState("");
  const [themeSaving, setThemeSaving] = useState(false);
  const [themeOptions, setThemeOptions] = useState<ThemeBackground[]>([]);
  const videoRef = useRef<HTMLVideoElement>(null);

  const load = useCallback(async () => {
    const [v, cats] = await Promise.all([getVideo(videoId), listCategories()]);
    setVideo(v);
    setCategories(cats.items);
    setSelectedTagIds(v.tags.map((t) => t.id));
    const labels: Record<number, string> = {};
    v.tags.forEach((t) => {
      labels[t.id] = t.name;
    });
    setTagLabels(labels);
  }, [videoId]);

  useEffect(() => {
    if (!Number.isFinite(videoId)) return;
    load().catch((e) => message.error(e instanceof Error ? e.message : "加载失败"));
  }, [videoId, load]);

  useEffect(() => {
    if (video) {
      setClipName(video.file_name);
    }
  }, [video]);

  const searchTags = async (text: string) => {
    setTagInput(text);
    const res = await listTags(text || undefined, 100);
    setTagOptions(res.items.map((t) => ({ value: t.name, id: t.id })));
  };

  const loadTagOptions = useCallback(async (text = "") => {
    const res = await listTags(text || undefined, 100);
    setTagOptions(res.items.map((t) => ({ value: t.name, id: t.id })));
  }, []);

  const save = async (patch: Record<string, unknown>, successMsg = "已保存") => {
    setSaving(true);
    try {
      const updated = await updateVideo(videoId, patch);
      setVideo(updated);
      setSelectedTagIds(updated.tags.map((t) => t.id));
      const labels: Record<number, string> = {};
      updated.tags.forEach((t) => {
        labels[t.id] = t.name;
      });
      setTagLabels(labels);
      message.success(successMsg);
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else message.error(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const saveTags = async (tagIds: number[]) => {
    await save({ tag_ids: tagIds }, "标签已保存");
  };

  const saveAllAnnotations = () => {
    void saveTags(selectedTagIds);
  };

  const addTagByName = async (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    try {
      const existing = tagOptions.find((o) => o.value === trimmed);
      const tag = existing ? { id: existing.id, name: trimmed } : await getOrCreateTag(trimmed);
      const nextIds = selectedTagIds.includes(tag.id) ? selectedTagIds : [...selectedTagIds, tag.id];
      setTagLabels((prev) => ({ ...prev, [tag.id]: tag.name }));
      setTagInput("");
      await saveTags(nextIds);
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else message.error(e instanceof Error ? e.message : "标签添加失败");
    }
  };

  const removeTag = (tagId: number) => {
    const nextIds = selectedTagIds.filter((id) => id !== tagId);
    void saveTags(nextIds);
  };

  useEffect(() => {
    listThemeBackgrounds({ page: 1, page_size: 100 })
      .then((r) => setThemeOptions(r.items))
      .catch(() => {});
    void loadTagOptions();
  }, [loadTagOptions]);

  if (!video) {
    return <div style={{ padding: 24 }}>加载中…</div>;
  }

  const canPlay = video.playback_supported && !video.missing;
  const canClip = !video.missing && video.has_audio;

  const saveThemeFromFrame = async () => {
    if (!canPlay) {
      message.warning("当前视频无法播放，无法截帧");
      return;
    }
    const timeSec = videoRef.current?.currentTime ?? currentTime;
    setThemeSaving(true);
    try {
      const bg = await createThemeBackgroundFromFrame(videoId, {
        time_sec: timeSec,
        name: themeName.trim() || null,
      });
      const updated = await getVideo(videoId);
      setVideo(updated);
      setThemeModalOpen(false);
      setThemeName("");
      message.success(`已设为主题背景图：${bg.name}`);
      listThemeBackgrounds({ page: 1, page_size: 100 })
        .then((r) => setThemeOptions(r.items))
        .catch(() => {});
    } catch (e) {
      message.error(e instanceof Error ? e.message : "保存失败");
    } finally {
      setThemeSaving(false);
    }
  };

  const changeThemeBackground = async (backgroundId: number) => {
    if (video?.theme_background?.id === backgroundId) return;
    setThemeSaving(true);
    try {
      const updated = await linkThemeBackground(videoId, backgroundId);
      setVideo(updated);
      message.success("主题背景图已更新");
    } catch (e) {
      message.error(e instanceof Error ? e.message : "更新失败");
    } finally {
      setThemeSaving(false);
    }
  };

  const submitClip = async () => {
    if (clipStart == null || Number.isNaN(clipStart)) {
      message.warning("请填写开始时间（秒）");
      return;
    }
    if (clipEnd != null && clipEnd <= clipStart) {
      message.warning("结束时间必须大于开始时间");
      return;
    }
    setClipping(true);
    try {
      const res = await createVideoClip({
        video_id: video.id,
        start_sec: clipStart,
        end_sec: clipEnd ?? undefined,
        output_file_name: clipName.trim() || undefined,
      });
      message.success(`截取任务已提交（Job #${res.job_id}）`);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "截取提交失败");
    } finally {
      setClipping(false);
    }
  };

  const submitDelete = () => {
    Modal.confirm({
      title: "删除视频",
      content: "删除后会将源文件移动到同目录的 _delete 文件夹，并从库中移除该视频记录。",
      okText: "确认删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await deleteVideo(video.id);
          message.success("已删除（移入 _delete）");
          navigate("/");
        } catch (e) {
          message.error(e instanceof Error ? e.message : "删除失败");
        }
      },
    });
  };

  return (
    <div className="page video-detail-page">
      <div className="video-detail-header">
        <div>
          <Space style={{ marginBottom: 8 }}>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
              返回
            </Button>
            <Link to="/">视频库</Link>
          </Space>
          <Title level={4} style={{ margin: 0 }}>
            {video.file_name}
          </Title>
          <Text type="secondary">
            {video.duration_sec ? `${Math.floor(video.duration_sec)} 秒` : "时长未知"} ·{" "}
            {video.width && video.height ? `${video.width}×${video.height}` : "分辨率未知"}
          </Text>
          <div style={{ marginTop: 8 }}>
            {video.metadata_status === "pending" && <Tag color="orange">元数据解析中</Tag>}
            {!video.has_audio && <Tag color="volcano">无音频</Tag>}
            {video.missing && <Tag color="red">文件缺失</Tag>}
          </div>
        </div>
        <Space>
          <Button danger icon={<DeleteOutlined />} disabled={video.missing} onClick={submitDelete}>
            删除
          </Button>
          <Button
            icon={<FolderOpenOutlined />}
            disabled={video.missing}
            onClick={() =>
              openVideoFolder(video.id).catch((e) =>
                message.error(e instanceof Error ? e.message : "打开失败")
              )
            }
          >
            打开目录
          </Button>
          <Button type="primary" onClick={() => setClipOpen(true)} disabled={!canClip}>
            截取
          </Button>
        </Space>
      </div>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} lg={16}>
          <div className="video-player-panel">
            {canPlay ? (
              <video
                ref={videoRef}
                controls
                style={{ width: "100%", maxHeight: 520, background: "#000" }}
                src={video.stream_url}
                onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
              />
            ) : (
              <div style={{ padding: 24, background: "#fafafa", borderRadius: 8 }}>
                <Paragraph>
                  <Text type="danger">当前编码浏览器无法播放</Text>
                </Paragraph>
                <Text type="secondary">
                  视频编码：{video.video_codec ?? "—"} · 音频编码：{video.audio_codec ?? "—"}
                </Text>
                {video.metadata_status !== "ready" && (
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary">元数据尚未就绪，请稍后再试</Text>
                  </div>
                )}
              </div>
            )}
            {canPlay && !video.theme_background && (
              <div style={{ marginTop: 12 }}>
                <Space wrap>
                  <Button
                    icon={<PictureOutlined />}
                    onClick={() => setThemeModalOpen(true)}
                    disabled={video.missing}
                  >
                    设为主题背景图（当前帧 {currentTime.toFixed(1)}s）
                  </Button>
                </Space>
              </div>
            )}
          </div>
        </Col>
        <Col xs={24} lg={8}>
          <div className="video-meta-panel" style={{ marginBottom: 16 }}>
            <div className="video-meta-title">
              <Text strong>主题背景图</Text>
            </div>
            <Select
              showSearch
              placeholder="选择主题背景图"
              style={{ width: "100%" }}
              value={video.theme_background?.id}
              loading={themeSaving}
              onChange={(id) => void changeThemeBackground(id)}
              optionFilterProp="label"
              options={themeOptions.map((t) => ({
                value: t.id,
                label: t.name,
              }))}
            />
            {video.theme_background && (
              <Link
                to={`/?theme_background_id=${video.theme_background.id}&theme_background_name=${encodeURIComponent(video.theme_background.name)}`}
                style={{ fontSize: 12, marginTop: 8, display: "inline-block" }}
              >
                查看关联视频
              </Link>
            )}
          </div>
          <div className="video-meta-panel">
            <div className="video-meta-title">
              <Text strong>标注</Text>
              <Button type="primary" size="small" loading={saving} onClick={saveAllAnnotations}>
                保存标签
              </Button>
            </div>
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              <div>
                <Text type="secondary">分类</Text>
                <Select
                  allowClear
                  style={{ width: "100%", marginTop: 6 }}
                  placeholder="选择分类"
                  value={video.category?.id ?? null}
                  options={categories.map((c) => ({ value: c.id, label: c.name }))}
                  onChange={(val) => save({ category_id: val ?? null })}
                />
              </div>
              <div>
                <Text type="secondary">标签</Text>
                <Select
                  showSearch
                  style={{ width: "100%", marginTop: 6 }}
                  placeholder="选择或输入标签，回车添加"
                  value={null}
                  searchValue={tagInput}
                  onSearch={searchTags}
                  onSelect={(val) => {
                    void addTagByName(String(val));
                    setTagInput("");
                  }}
                  onFocus={() => {
                    if (tagOptions.length === 0) void loadTagOptions();
                  }}
                  filterOption={false}
                  optionFilterProp="label"
                  options={tagOptions.map((o) => ({ value: o.value, label: o.value }))}
                  onInputKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void addTagByName(tagInput);
                      setTagInput("");
                    }
                  }}
                />
                <div style={{ marginTop: 8 }}>
                  {selectedTagIds.map((tid) => (
                    <Tag
                      key={tid}
                      closable
                      onClose={(e) => {
                        e.preventDefault();
                        removeTag(tid);
                      }}
                    >
                      {tagLabels[tid] ?? `标签#${tid}`}
                    </Tag>
                  ))}
                </div>
              </div>
              <div>
                <Text type="secondary">录制开始时间</Text>
                <DatePicker
                  showTime
                  style={{ width: "100%", marginTop: 6 }}
                  value={toDayjs(video.record_start_at)}
                  onChange={(d) => save({ record_start_at: fromDayjs(d) })}
                />
              </div>
              <div>
                <Text type="secondary">录制结束时间</Text>
                <DatePicker
                  showTime
                  style={{ width: "100%", marginTop: 6 }}
                  value={toDayjs(video.record_end_at)}
                  onChange={(d) => save({ record_end_at: fromDayjs(d) })}
                />
              </div>
              <div>
                <Text type="secondary">喜爱度（0=未设置，1～10）</Text>
                <div style={{ marginTop: 6 }}>
                  <InputNumber
                    min={0}
                    max={10}
                    value={video.favorite_level}
                    onChange={(val) => {
                      if (val != null) save({ favorite_level: val });
                    }}
                  />
                  <div style={{ marginTop: 8 }}>
                    <FavoriteStars level={video.favorite_level} />
                  </div>
                </div>
              </div>
            </Space>
          </div>
        </Col>
      </Row>

      <Drawer
        title="单段截取"
        open={clipOpen}
        onClose={() => setClipOpen(false)}
        width={420}
        footer={
          <Button type="primary" block onClick={submitClip} loading={clipping} disabled={!canClip}>
            提交截取任务
          </Button>
        }
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Text type="secondary">
            输出到源目录 <Text code>_temp</Text> 子目录；同名覆盖，原文件保留。
          </Text>
          <InputNumber
            style={{ width: "100%" }}
            min={0}
            precision={3}
            value={clipStart}
            onChange={(v) => setClipStart(v)}
            placeholder="开始时间（秒，必填）"
            disabled={!canClip}
          />
          <InputNumber
            style={{ width: "100%" }}
            min={0}
            precision={3}
            value={clipEnd}
            onChange={(v) => setClipEnd(v)}
            placeholder="结束时间（秒，可空=到末尾）"
            disabled={!canClip}
          />
          <Input
            value={clipName}
            onChange={(e) => setClipName(e.target.value)}
            placeholder="输出文件名（默认源文件名）"
            disabled={!canClip}
          />
          {!canClip && (
            <Text type="danger">
              {video.missing ? "文件缺失，无法截取" : "无音频轨视频无法截取"}
            </Text>
          )}
        </Space>
      </Drawer>

      <Modal
        title="设为主题背景图"
        open={themeModalOpen}
        onCancel={() => setThemeModalOpen(false)}
        onOk={() => void saveThemeFromFrame()}
        okText="保存当前帧"
        confirmLoading={themeSaving}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Text type="secondary">
            将使用当前播放位置 <Text code>{currentTime.toFixed(2)}</Text> 秒处的画面。
          </Text>
          <Input
            value={themeName}
            onChange={(e) => setThemeName(e.target.value)}
            placeholder="名称（可中文，留空自动生成 room_0001）"
            maxLength={64}
          />
        </Space>
      </Modal>
    </div>
  );
}
