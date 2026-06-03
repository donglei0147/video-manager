import {
  AppstoreOutlined,
  BarsOutlined,
  CloseOutlined,
  FilterOutlined,
  ScissorOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import {
  Button,
  Drawer,
  Input,
  InputNumber,
  Modal,
  Pagination,
  Radio,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
  message,
} from "antd";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { listCategories, type Category } from "../api/categories";
import { getOrCreateTag, listTags, type TagItem } from "../api/tags";
import {
  createMergeVideos,
  deleteVideo,
  listVideos,
  mergeVideosPreflight,
  type VideoListParams,
} from "../api/videos";
import type { VideoSummary } from "../api/types";
import VideoCard from "../components/VideoCard";

const { Title } = Typography;

const PAGE_SIZE_OPTIONS = [24, 48, 100];

const SORT_OPTIONS = [
  { value: "file_mtime_desc", label: "修改时间 ↓" },
  { value: "file_mtime_asc", label: "修改时间 ↑" },
  { value: "favorite_desc", label: "喜爱度 ↓" },
  { value: "favorite_asc", label: "喜爱度 ↑" },
  { value: "record_start_desc", label: "录制开始 ↓" },
  { value: "record_start_asc", label: "录制开始 ↑" },
];

export default function LibraryPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const themeBackgroundIdParam = searchParams.get("theme_background_id");
  const themeBackgroundNameParam = searchParams.get("theme_background_name");
  const initialThemeBackgroundId = themeBackgroundIdParam
    ? Number(themeBackgroundIdParam)
    : undefined;

  const [videos, setVideos] = useState<VideoSummary[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(24);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [includeMissing, setIncludeMissing] = useState(false);
  const [loadThumbnails, setLoadThumbnails] = useState(true);
  const [sort, setSort] = useState("file_mtime_desc");

  const [categories, setCategories] = useState<Category[]>([]);
  const [allTags, setAllTags] = useState<TagItem[]>([]);
  const [newTagName, setNewTagName] = useState("");
  const [creatingTag, setCreatingTag] = useState(false);
  const [categoryId, setCategoryId] = useState<number | undefined>();
  const [tagIds, setTagIds] = useState<number[]>([]);
  const [keyword, setKeyword] = useState("");
  const [recordStartFrom, setRecordStartFrom] = useState("");
  const [recordStartTo, setRecordStartTo] = useState("");
  const [noRecordTime, setNoRecordTime] = useState(false);
  const [favoriteMin, setFavoriteMin] = useState<number | undefined>();
  const [themeBackgroundId, setThemeBackgroundId] = useState<number | undefined>(
    Number.isFinite(initialThemeBackgroundId) ? initialThemeBackgroundId : undefined
  );
  const [themeBackgroundLabel, setThemeBackgroundLabel] = useState(
    themeBackgroundNameParam ?? ""
  );
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [mergeSubmitting, setMergeSubmitting] = useState(false);
  const [mergeName, setMergeName] = useState("");
  const [filterOpen, setFilterOpen] = useState(false);

  const refreshAllTags = useCallback(async () => {
    const r = await listTags(undefined, 100);
    setAllTags(r.items);
  }, []);

  useEffect(() => {
    listCategories()
      .then((r) => setCategories(r.items))
      .catch(() => {});
    refreshAllTags().catch(() => {});
  }, [refreshAllTags]);

  const buildParams = useCallback((): VideoListParams => {
    const p: VideoListParams = {
      page,
      page_size: pageSize,
      include_missing: includeMissing,
      sort,
    };
    if (categoryId != null) p.category_id = categoryId;
    if (tagIds.length) p.tag_ids = tagIds;
    if (keyword.trim()) p.q = keyword.trim();
    if (recordStartFrom) p.record_start_from = recordStartFrom;
    if (recordStartTo) p.record_start_to = recordStartTo;
    if (noRecordTime) p.has_record_time = false;
    if (favoriteMin != null) p.favorite_min = favoriteMin;
    if (themeBackgroundId != null) p.theme_background_id = themeBackgroundId;
    return p;
  }, [
    page,
    pageSize,
    includeMissing,
    sort,
    categoryId,
    tagIds,
    keyword,
    recordStartFrom,
    recordStartTo,
    noRecordTime,
    favoriteMin,
    themeBackgroundId,
  ]);

  const fetchList = useCallback(async () => {
    setLoading(true);
    setLoadThumbnails(false);
    try {
      const data = await listVideos(buildParams());
      setVideos(data.items);
      setTotal(data.total);
      setSelectedIds((prev) => prev.filter((id) => data.items.some((v) => v.id === id)));
      setLoadThumbnails(true);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [buildParams]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible") fetchList();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [fetchList]);

  const onPageChange = (p: number, ps?: number) => {
    setLoadThumbnails(false);
    setPage(p);
    if (ps && ps !== pageSize) {
      setPageSize(ps);
      setPage(1);
    }
  };

  const applyFilters = () => {
    setPage(1);
    fetchList();
  };

  const resetFilters = () => {
    setCategoryId(undefined);
    setTagIds([]);
    setKeyword("");
    setRecordStartFrom("");
    setRecordStartTo("");
    setNoRecordTime(false);
    setFavoriteMin(undefined);
    setThemeBackgroundId(undefined);
    setThemeBackgroundLabel("");
    setSearchParams({});
    setPage(1);
  };

  const handleCreateTag = async () => {
    const name = newTagName.trim();
    if (!name) {
      message.warning("请输入标签名");
      return;
    }
    setCreatingTag(true);
    try {
      const created = await getOrCreateTag(name);
      await refreshAllTags();
      setTagIds((prev) => (prev.includes(created.id) ? prev : [...prev, created.id]));
      setNewTagName("");
      message.success(`标签「${created.name}」已保存`);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "保存标签失败");
    } finally {
      setCreatingTag(false);
    }
  };

  const selectedVideos = selectedIds
    .map((id) => videos.find((v) => v.id === id))
    .filter((v): v is VideoSummary => Boolean(v));

  const moveSelected = (id: number, dir: "up" | "down") => {
    setSelectedIds((prev) => {
      const i = prev.indexOf(id);
      if (i < 0) return prev;
      const j = dir === "up" ? i - 1 : i + 1;
      if (j < 0 || j >= prev.length) return prev;
      const next = [...prev];
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
  };

  const activeFilterCount = [
    categoryId != null,
    tagIds.length > 0,
    keyword.trim().length > 0,
    recordStartFrom.length > 0,
    recordStartTo.length > 0,
    noRecordTime,
    favoriteMin != null,
    includeMissing,
    themeBackgroundId != null,
  ].filter(Boolean).length;

  const openMergeModal = () => {
    if (selectedIds.length < 2) {
      message.warning("请至少选择 2 个视频进行合并");
      return;
    }
    const first = selectedVideos[0];
    setMergeName(first?.file_name ?? "");
    setMergeOpen(true);
  };

  const submitMerge = async () => {
    if (selectedIds.length < 2) {
      message.warning("请至少选择 2 个视频进行合并");
      return;
    }
    setMergeSubmitting(true);
    try {
      await mergeVideosPreflight(selectedIds);
      const res = await createMergeVideos({
        video_ids: selectedIds,
        output_file_name: mergeName.trim() || undefined,
      });
      message.success(`合并任务已提交（Job #${res.job_id}）`);
      setMergeOpen(false);
      setSelectedIds([]);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "合并提交失败");
    } finally {
      setMergeSubmitting(false);
    }
  };

  const handleDeleteVideo = async (videoId: number) => {
    try {
      await deleteVideo(videoId);
      message.success("已删除（移入 _delete）");
      await fetchList();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "删除失败");
    }
  };

  return (
    <div className="page library-page">
      <div className="page-header">
        <Title level={3} style={{ margin: 0 }}>视频库</Title>
        {themeBackgroundId != null && (
          <Tag
            closable
            color="purple"
            onClose={() => {
              setThemeBackgroundId(undefined);
              setThemeBackgroundLabel("");
              setSearchParams({});
              setPage(1);
            }}
            style={{ marginTop: 8 }}
          >
            主题背景图：{themeBackgroundLabel || `#${themeBackgroundId}`}
          </Tag>
        )}
        <Space wrap>
          <Input.Search
            placeholder="搜索文件名 / 路径关键词"
            allowClear
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={applyFilters}
            style={{ width: 280 }}
          />
          <Select
            value={sort}
            onChange={setSort}
            options={SORT_OPTIONS}
            style={{ width: 160 }}
          />
          <Radio.Group
            value={viewMode}
            onChange={(e) => setViewMode(e.target.value)}
            optionType="button"
            buttonStyle="solid"
          >
            <Radio.Button value="grid">
              <AppstoreOutlined />
            </Radio.Button>
            <Radio.Button value="list">
              <BarsOutlined />
            </Radio.Button>
          </Radio.Group>
          <Select
            value={pageSize}
            onChange={(v) => {
              setPageSize(v);
              setPage(1);
            }}
            options={PAGE_SIZE_OPTIONS.map((n) => ({ value: n, label: `每页 ${n}` }))}
            style={{ width: 110 }}
          />
          <Button icon={<FilterOutlined />} onClick={() => setFilterOpen(true)}>
            筛选{activeFilterCount > 0 ? `（${activeFilterCount}）` : ""}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchList} loading={loading}>
            刷新
          </Button>
        </Space>
      </div>

      {selectedIds.length > 0 && (
        <div className="library-batch-bar">
          <Space wrap>
            <span>已选择 {selectedIds.length} 个视频</span>
            <Button icon={<ScissorOutlined />} type="primary" onClick={openMergeModal} disabled={selectedIds.length < 2}>
              合并已选
            </Button>
            <Button icon={<CloseOutlined />} onClick={() => setSelectedIds([])}>
              清空选择
            </Button>
          </Space>
        </div>
      )}

      <div className={viewMode === "grid" ? "video-grid" : "video-list"}>
        {videos.map((v) => (
          <VideoCard
            key={v.id}
            video={v}
            loadThumbnail={loadThumbnails}
            viewMode={viewMode}
            onDelete={handleDeleteVideo}
            selectable={!v.missing}
            selected={selectedIds.includes(v.id)}
            onSelectChange={(videoId, checked) => {
              setSelectedIds((prev) => {
                if (checked) return prev.includes(videoId) ? prev : [...prev, videoId];
                return prev.filter((id) => id !== videoId);
              });
            }}
          />
        ))}
      </div>

      {!loading && videos.length === 0 && (
        <div style={{ textAlign: "center", padding: 48, color: "#999" }}>
          暂无视频。请先在「设置」中添加扫描文件夹并执行扫描。
        </div>
      )}

      <div className="pagination-bar">
        <Pagination
          current={page}
          pageSize={pageSize}
          total={total}
          showSizeChanger
          pageSizeOptions={PAGE_SIZE_OPTIONS.map(String)}
          onChange={onPageChange}
          showTotal={(t) => `共 ${t} 个视频`}
        />
      </div>

      <Drawer
        title="筛选与排序"
        open={filterOpen}
        onClose={() => setFilterOpen(false)}
        width={380}
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Select
            allowClear
            placeholder="分类"
            style={{ width: "100%" }}
            value={categoryId}
            onChange={setCategoryId}
            options={categories.map((c) => ({ value: c.id, label: c.name }))}
          />
          <Select
            mode="multiple"
            placeholder="标签（AND）"
            style={{ width: "100%" }}
            value={tagIds}
            onChange={setTagIds}
            options={allTags.map((t) => ({ value: t.id, label: t.name }))}
          />
          <Input.Search
            placeholder="输入标签名，回车新增"
            enterButton="新增标签"
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            onSearch={() => {
              void handleCreateTag();
            }}
            loading={creatingTag}
          />
          <InputNumber
            min={1}
            max={10}
            placeholder="喜爱度 ≥"
            value={favoriteMin}
            onChange={(v) => setFavoriteMin(v ?? undefined)}
            style={{ width: "100%" }}
          />
          <Input
            placeholder="录制开始 ≥ YYYY-MM-DD HH:MM:SS"
            value={recordStartFrom}
            onChange={(e) => setRecordStartFrom(e.target.value)}
          />
          <Input
            placeholder="录制开始 ≤ YYYY-MM-DD HH:MM:SS"
            value={recordStartTo}
            onChange={(e) => setRecordStartTo(e.target.value)}
          />
          <Space>
            <span>仅未填录制时间</span>
            <Switch checked={noRecordTime} onChange={setNoRecordTime} />
          </Space>
          <Space>
            <span>显示缺失视频</span>
            <Switch checked={includeMissing} onChange={setIncludeMissing} />
          </Space>
          <Space>
            <Button
              type="primary"
              onClick={() => {
                applyFilters();
                setFilterOpen(false);
              }}
            >
              应用筛选
            </Button>
            <Button onClick={resetFilters}>重置</Button>
          </Space>
        </Space>
      </Drawer>

      <Modal
        title="多视频合并"
        open={mergeOpen}
        onCancel={() => setMergeOpen(false)}
        onOk={submitMerge}
        okText="提交合并任务"
        confirmLoading={mergeSubmitting}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Input
            value={mergeName}
            onChange={(e) => setMergeName(e.target.value)}
            placeholder="输出文件名（默认第一个源视频文件名）"
          />
          <div style={{ maxHeight: 240, overflow: "auto", border: "1px solid #f0f0f0", borderRadius: 8, padding: 8 }}>
            {selectedVideos.map((v, i) => (
              <div key={v.id} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
                <span style={{ width: 24 }}>{i + 1}.</span>
                <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {v.file_name}
                </span>
                <Button size="small" onClick={() => moveSelected(v.id, "up")} disabled={i === 0}>
                  上移
                </Button>
                <Button size="small" onClick={() => moveSelected(v.id, "down")} disabled={i === selectedVideos.length - 1}>
                  下移
                </Button>
              </div>
            ))}
          </div>
        </Space>
      </Modal>
    </div>
  );
}
