# UI Overhaul Notes

本次改造仅重构前端展现层与布局层，未主动修改 API 路径、store 业务逻辑、交互分支与任务流转逻辑。

## 主要改动

- 顶层布局改为侧边导航 + 工作区
- 检索页改为主工作台 + 右侧信息栏
- 资源准备页改为概览卡片 + 双栏控制台布局
- 资源管理页改为概览卡片 + 管理面板 + 侧边摘要
- 新增 overhaul.css 作为视觉与布局覆盖层
- 补充若干 aria 语义与 focus-visible 焦点样式
- 修正 TaskTable 名称列展示问题

## 主要改动文件

- src/main.ts
- src/layouts/AppLayout.vue
- src/components/common/TopPrimaryNav.vue
- src/components/common/ErrorBanner.vue
- src/components/common/EmptyState.vue
- src/components/common/LoadingBlock.vue
- src/components/search/SearchHeroInput.vue
- src/components/search/ResultDetailModal.vue
- src/components/prepare/TaskTable.vue
- src/views/SearchPage.vue
- src/views/PreparePage.vue
- src/views/StoreManagePage.vue
- src/assets/styles/overhaul.css

## 验证说明

当前交付环境中未包含 node_modules，因此没有直接执行 npm run build。
已完成静态文件检查与人工代码核对。你本地安装依赖后可继续执行：

```bash
npm install
npm run dev
npm run build
```
