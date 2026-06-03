import { AppstoreOutlined, FolderOpenOutlined, PictureOutlined, TagsOutlined, VideoCameraOutlined } from "@ant-design/icons";
import { Layout, Menu } from "antd";
import { useMemo } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import LibraryPage from "./pages/LibraryPage";
import CategoryManagePage from "./pages/CategoryManagePage";
import TagManagePage from "./pages/TagManagePage";
import ThemeBackgroundManagePage from "./pages/ThemeBackgroundManagePage";
import SettingsPage from "./pages/SettingsPage";
import VideoDetailPage from "./pages/VideoDetailPage";
import "./App.css";

const { Header, Content } = Layout;

function AppLayout() {
  const location = useLocation();
  const selected = useMemo(() => {
    if (location.pathname.startsWith("/settings")) return "settings";
    if (location.pathname.startsWith("/tags")) return "tags";
    if (location.pathname.startsWith("/categories")) return "categories";
    if (location.pathname.startsWith("/theme-backgrounds")) return "theme-backgrounds";
    return "library";
  }, [location.pathname]);

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header className="app-header">
        <div className="logo">个人视频管理</div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[selected]}
          items={[
            {
              key: "library",
              icon: <VideoCameraOutlined />,
              label: <Link to="/">视频库</Link>,
            },
            {
              key: "settings",
              icon: <FolderOpenOutlined />,
              label: <Link to="/settings">设置</Link>,
            },
            {
              key: "theme-backgrounds",
              icon: <PictureOutlined />,
              label: <Link to="/theme-backgrounds">主题背景图</Link>,
            },
            {
              key: "tags",
              icon: <TagsOutlined />,
              label: <Link to="/tags">标签管理</Link>,
            },
            {
              key: "categories",
              icon: <AppstoreOutlined />,
              label: <Link to="/categories">分类管理</Link>,
            },
          ]}
        />
      </Header>
      <Content className="app-content">
        <Routes>
          <Route path="/" element={<LibraryPage />} />
          <Route path="/videos/:id" element={<VideoDetailPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/tags" element={<TagManagePage />} />
          <Route path="/theme-backgrounds" element={<ThemeBackgroundManagePage />} />
          <Route path="/categories" element={<CategoryManagePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Content>
    </Layout>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
