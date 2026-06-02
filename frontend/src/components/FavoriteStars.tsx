import { StarFilled, StarOutlined } from "@ant-design/icons";

interface Props {
  level: number;
}

/** 0 = 未设置；1-10 显示星级（每 2 分一颗星，最多 5 颗） */
export default function FavoriteStars({ level }: Props) {
  if (level === 0) {
    return <span style={{ color: "#999" }}>未设置</span>;
  }
  const stars = Math.min(5, Math.ceil(level / 2));
  return (
    <span>
      {Array.from({ length: 5 }).map((_, i) =>
        i < stars ? (
          <StarFilled key={i} style={{ color: "#faad14" }} />
        ) : (
          <StarOutlined key={i} style={{ color: "#d9d9d9" }} />
        )
      )}
      <span style={{ marginLeft: 4, fontSize: 12, color: "#666" }}>{level}</span>
    </span>
  );
}
