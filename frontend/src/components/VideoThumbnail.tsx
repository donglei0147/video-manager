import { FileImageOutlined } from "@ant-design/icons";
import { Spin } from "antd";
import { useVideoThumbnail } from "../hooks/useVideoThumbnail";

interface Props {
  streamUrl: string;
  enabled: boolean;
  alt: string;
}

export default function VideoThumbnail({ streamUrl, enabled, alt }: Props) {
  const { thumbUrl, failed, loading } = useVideoThumbnail(streamUrl, enabled);

  if (failed || (!loading && !thumbUrl)) {
    return (
      <div className="thumb-placeholder" title={alt}>
        <FileImageOutlined style={{ fontSize: 32, color: "#bbb" }} />
      </div>
    );
  }

  if (loading || !thumbUrl) {
    return (
      <div className="thumb-placeholder">
        <Spin size="small" />
      </div>
    );
  }

  return <img src={thumbUrl} alt={alt} className="thumb-img" />;
}
