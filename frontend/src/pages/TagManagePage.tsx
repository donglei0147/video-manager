import { DeleteOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Form, Input, Popconfirm, Table, Typography, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { deleteTag, getOrCreateTag, listTags, type TagItem } from "../api/tags";

const { Title, Text } = Typography;

type TagFormValues = {
  name: string;
};

export default function TagManagePage() {
  const [items, setItems] = useState<TagItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm<TagFormValues>();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listTags(undefined, 100);
      setItems(data.items);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "标签加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await getOrCreateTag(values.name);
      form.resetFields();
      message.success("标签已保存");
      await load();
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else if (e instanceof Error && e.message) message.error(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const columns: ColumnsType<TagItem> = [
    { title: "ID", dataIndex: "id", width: 80 },
    { title: "名称", dataIndex: "name" },
    {
      title: "操作",
      width: 120,
      render: (_, row) => (
        <Popconfirm
          title={`确认删除标签「${row.name}」？`}
          description="将解除所有视频与该标签的关联。"
          onConfirm={() => {
            void (async () => {
              try {
                await deleteTag(row.id);
                message.success("标签已删除");
                await load();
              } catch (e) {
                message.error(e instanceof Error ? e.message : "删除失败");
              }
            })();
          }}
        >
          <Button size="small" danger icon={<DeleteOutlined />}>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div className="page tag-manage-page">
      <div className="page-header">
        <Title level={3} style={{ margin: 0 }}>
          标签管理
        </Title>
        <Button icon={<ReloadOutlined />} onClick={() => void load()} loading={loading}>
          刷新
        </Button>
      </div>

      <Card size="small" title="新增标签">
        <Form
          form={form}
          layout="inline"
          onFinish={() => {
            void handleCreate();
          }}
        >
          <Form.Item
            name="name"
            rules={[
              { required: true, message: "请输入标签名称" },
              { max: 64, message: "标签名称不超过 64 字符" },
            ]}
          >
            <Input placeholder="标签名称" style={{ width: 240 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<PlusOutlined />} htmlType="submit" loading={submitting}>
              保存
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card size="small" title="标签列表" style={{ marginTop: 16 }}>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={false}
          size="middle"
        />
      </Card>

      <Text type="secondary" style={{ display: "block", marginTop: 16 }}>
        给视频打标签请在视频详情页操作；此处仅维护全局标签池。
      </Text>
    </div>
  );
}
