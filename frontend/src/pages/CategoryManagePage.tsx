import { DeleteOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Form, Input, InputNumber, Popconfirm, Space, Table, Typography, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useState } from "react";
import {
  createCategory,
  deleteCategory,
  listCategories,
  updateCategory,
  type Category,
} from "../api/categories";

const { Title, Text } = Typography;

type CategoryFormValues = {
  name: string;
  sort_order: number;
};

export default function CategoryManagePage() {
  const [items, setItems] = useState<Category[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm<CategoryFormValues>();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listCategories();
      setItems(data.items);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "分类加载失败");
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
      await createCategory(values.name, values.sort_order);
      form.resetFields();
      message.success("分类已创建");
      await load();
    } catch (e) {
      if (e instanceof Error && e.message) {
        message.error(e.message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleRename = async (id: number, currentName: string) => {
    const nextName = window.prompt("请输入新的分类名称：", currentName);
    if (nextName == null) return;
    const trimmed = nextName.trim();
    if (!trimmed) {
      message.warning("分类名称不能为空");
      return;
    }
    try {
      await updateCategory(id, { name: trimmed });
      message.success("分类名称已更新");
      await load();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "更新失败");
    }
  };

  const columns: ColumnsType<Category> = [
    { title: "ID", dataIndex: "id", width: 80 },
    { title: "名称", dataIndex: "name" },
    { title: "排序", dataIndex: "sort_order", width: 100 },
    { title: "视频数", dataIndex: "video_count", width: 100 },
    {
      title: "操作",
      width: 220,
      render: (_, row) => (
        <Space>
          <Button size="small" onClick={() => void handleRename(row.id, row.name)}>
            重命名
          </Button>
          <Popconfirm
            title={`确认删除分类「${row.name}」？`}
            description="关联视频将保留，仅清空其分类。"
            onConfirm={() => {
              void (async () => {
                try {
                  await deleteCategory(row.id);
                  message.success("分类已删除");
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
        </Space>
      ),
    },
  ];

  return (
    <div className="page category-manage-page">
      <div className="page-header">
        <Title level={3} style={{ margin: 0 }}>
          分类管理
        </Title>
        <Button icon={<ReloadOutlined />} onClick={() => void load()} loading={loading}>
          刷新
        </Button>
      </div>

      <Card size="small" title="新增分类">
        <Form
          form={form}
          layout="inline"
          initialValues={{ sort_order: 0 }}
          onFinish={() => {
            void handleCreate();
          }}
        >
          <Form.Item
            name="name"
            rules={[
              { required: true, message: "请输入分类名称" },
              { max: 64, message: "分类名称不超过 64 字符" },
            ]}
          >
            <Input placeholder="分类名称" style={{ width: 240 }} />
          </Form.Item>
          <Form.Item name="sort_order">
            <InputNumber placeholder="排序" style={{ width: 120 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<PlusOutlined />} htmlType="submit" loading={submitting}>
              新增
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card size="small" title="分类列表" style={{ marginTop: 16 }}>
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
        删除分类仅取消视频与该分类的关联，不会删除视频文件。
      </Text>
    </div>
  );
}
