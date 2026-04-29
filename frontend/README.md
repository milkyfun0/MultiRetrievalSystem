# 多模态检索系统前端

这是一个基于 Vue 3 + Vite + TypeScript + Pinia + Vue Router + Axios 的前端骨架工程，已按你提供的前端设计稿、后端技术说明文档、算法端技术说明文档对齐。

## 已对齐的接口

### 检索
- `POST /api/v1/search`

### 资源准备
- `POST /api/v1/vectorize`
- `GET /api/v1/tasks/{job_id}`

### 健康检查
- `GET /api/v1/health`

## 运行

```bash
npm install
npm run dev
```

默认地址：

```text
http://localhost:5173
```

## 打包

```bash
npm run build
```

## 环境变量

可选配置 `VITE_API_BASE_URL` 指向后端地址，例如：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

如果前端和后端使用同域反向代理，也可以保持默认 `/`。

## 当前实现说明

- 检索页支持 `Text2Video`、`Text2Image`、`Image2Image`
- 资源准备页支持提交任务、轮询状态、查看详情、重试
- 搜索结果支持网格视图和 Rank 流视图
- 结果详情使用弹窗
- 顶部显示服务健康状态

## Image2Image 当前约束

当前后端协议使用 `input.image_object_keys`，因此本前端第一版按 Object Key 对齐请求。页面保留了本地拖拽预览区，但真正提交给后端的是图片 Object Key 列表。


## 本地联调

默认开发代理会把 `/api/*` 转发到 `http://127.0.0.1:8000`。

如果你的后端地址不同，可以在项目根目录新建 `.env.local`。

```bash
VITE_BACKEND_PROXY_TARGET=http://127.0.0.1:8000
```
