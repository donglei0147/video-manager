import {
  DeleteOutlined,
  EditOutlined,
  ReloadOutlined,
  ZoomInOutlined,
} from "@ant-design/icons";
import {
  Button,
  Image,
  Input,
  Pagination,
  Popconfirm,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  deleteThemeBackground,
  listThemeBackgrounds,
  updateThemeBackground,
  type ThemeBackground,
} from "../api/themeBackgrounds";

const { Title, Text } = Typography;

export default function ThemeBackgroundManagePage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<ThemeBackground[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(48);
  const [total, setTotal] = useState(0);
  const [keyword, setKeyword] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewSrc, setPreviewSrc] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listThemeBackgrounds({
        page,
        page_size: pageSize,
        keyword: keyword || undefined,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, keyword]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleRename = async (item: ThemeBackground, e: React.MouseEvent) => {
    e.stopPropagation();
    const nextName = window.prompt("请输入新的名称：", item.name);
    if (nextName == null) return;
    const trimmed = nextName.trim();
    if (!trimmed) {
      message.warning("名称不能为空");
      return;
    }
    try {
      await updateThemeBackground(item.id, trimmed);
      message.success("名称已更新");
      await load();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "更新失败");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteThemeBackground(id);
      message.success("已删除");
      await load();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "删除失败");
    }
  };

  const openVideos = (item: ThemeBackground, e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (item.video_count <= 0) {
      message.info("当前背景图未关联视频");
      return;
    }
    navigate(
      `/?theme_background_id=${item.id}&theme_background_name=${encodeURIComponent(item.name)}`
    );
  };

  const openPreview = (item: ThemeBackground, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setPreviewSrc(item.image_url);
    setPreviewOpen(true);
  };

  return (
    <div className="page theme-background-page">
      <div className="page-header">
        <Title level={3} style={{ margin: 0 }}>
          主题背景图
        </Title>
        <Space wrap>
          <Input.Search
            placeholder="搜索名称"
            allowClear
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onSearch={(v) => {
              setKeyword(v.trim());
              setPage(1);
            }}
            style={{ width: 260 }}
          />
          <Button icon={<ReloadOutlined />} onClick={() => void load()} loading={loading}>
            刷新
          </Button>
          <Link to="/">返回视频库</Link>
        </Space>
      </div>

      <div className="theme-background-grid">
        {items.map((item) => (
          <div key={item.id} className="theme-background-card">
            <div
              className="theme-background-thumb"
              onClick={() => openPreview(item)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter") openPreview(item);
              }}
            >
              <img src={item.image_url} alt={item.name} loading="lazy" />
              <div className="theme-background-overlay">
                <div className="theme-background-overlay-top">
                  <Tag color={item.video_count > 0 ? "blue" : "default"}>
                    {item.video_count} 视频
                  </Tag>
                  <Button
                    type="text"
                    size="small"
                    className="theme-background-overlay-btn"
                    icon={<ZoomInOutlined />}
                    onClick={(e) => openPreview(item, e)}
                    title="放大"
                  />
                </div>
                <div className="theme-background-overlay-bottom">
                  <Text
                    strong
                    className="theme-background-overlay-name"
                    ellipsis
                    onClick={(e) => openVideos(item, e)}
                  >
                    {item.name}
                  </Text>
                  <Space size={4} wrap className="theme-background-overlay-actions">
                    <Button
                      type="text"
                      size="small"
                      className="theme-background-overlay-btn"
                      icon={<EditOutlined />}
                      onClick={(e) => void handleRename(item, e)}
                    >
                      重命名
                    </Button>
                    <Popconfirm
                      title="删除主题背景图"
                      description="将解除所有视频关联并删除图片文件。"
                      okText="确认删除"
                      cancelText="取消"
                      onConfirm={() => void handleDelete(item.id)}
                      onPopupClick={(e) => e.stopPropagation()}
                    >
                      <Button
                        type="text"
                        size="small"
                        danger
                        className="theme-background-overlay-btn"
                        icon={<DeleteOutlined />}
                        onClick={(e) => e.stopPropagation()}
                      >
                        删除
                      </Button>
                    </Popconfirm>
                  </Space>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {!loading && items.length === 0 && (
        <div style={{ textAlign: "center", padding: 48, color: "#999" }}>
          暂无主题背景图。可在视频详情页从播放帧创建。
        </div>
      )}

      <div className="pagination-bar">
        <Pagination
          current={page}
          pageSize={pageSize}
          total={total}
          onChange={setPage}
          showTotal={(t) => `共 ${t} 张`}
        />
      </div>

      <Image
        style={{ display: "none" }}
        preview={{
          visible: previewOpen,
          src: previewSrc,
          onVisibleChange: (visible) => setPreviewOpen(visible),
        }}
      />
    </div>
  );
}
