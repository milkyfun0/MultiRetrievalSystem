# 局域网部署小白操作指南

> 适用于：算法+后端部署在 Windows 机器（Pycharm 运行），前端在另一台教室电脑运行演示

## 1. 部署架构

```
┌─────────────┐     ┌─────────────┐
│  前端电脑   │────▶│ Windows 机器 │
│  教室电脑   │     │  算法+后端   │
│ 5173 端口   │     │ 8000 端口    │
└─────────────┘     └─────────────┘
```

- **Windows 机器**：运行算法服务 + 后端服务
- **教室电脑**：运行前端代码，通过浏览器访问 `http://localhost:5173`

## 2. Windows 机器配置（算法+后端）

### 2.1 环境准备

1. **安装 Python 3.8+**
   - 下载地址：https://www.python.org/downloads/
   - 安装时勾选 "Add Python to PATH"

2. **安装 Pycharm**（已安装可跳过）
   - 下载地址：https://www.jetbrains.com/pycharm/download/

3. **安装依赖**
   ```cmd
   cd algorithm
   pip install -r requirements.txt
   
   cd backend
   pip install -r requirements.txt
   ```

### 2.2 启动算法服务

1. **打开命令提示符**（Win+R 输入 `cmd`）
2. **进入项目目录**：
   ```cmd
   cd 你的项目路径\algorithm
   ```
3. **设置环境变量并启动**：
   ```cmd
   set I2I_CKPT_PATH=你的模型路径\i2i
   set T2I_CKPT_PATH=你的模型路径\t2i
   set T2V_CKPT_PATH=你的模型路径\t2v
   set MMR_GATEWAY_HOST=0.0.0.0
   set MMR_GATEWAY_PORT=18080
   
   python launcher/run_all.py
   ```

4. **验证算法服务**：
   打开浏览器访问 `http://localhost:18080/health`，应该看到算法服务状态

### 2.3 启动后端服务

1. **打开新的命令提示符**
2. **进入后端目录**：
   ```cmd
   cd 你的项目路径\backend
   ```
3. **设置环境变量并启动**：
   ```cmd
   set MMR_ALGORITHM_MODE=http
   set MMR_ALGORITHM_GATEWAY_URL=http://127.0.0.1:18080
   set MMR_ALGORITHM_TIMEOUT=600
   set MMR_DEMO_MODE=true
   
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. **验证后端服务**：
   打开浏览器访问 `http://localhost:8000/api/v1/health`，应该看到健康状态

### 2.4 获取 Windows 机器 IP 地址

1. **打开命令提示符**
2. **输入命令**：
   ```cmd
   ipconfig
   ```
3. **查找 IPv4 地址**（例如：`192.168.1.100`）

## 3. 教室电脑配置（前端）

### 3.1 环境准备

1. **安装 Node.js 16+**
   - 下载地址：https://nodejs.org/zh-cn/download/
   - 安装 LTS 版本即可

2. **安装 VS Code**（推荐，可选）
   - 下载地址：https://code.visualstudio.com/

### 3.2 启动前端服务

1. **打开终端/命令提示符**
2. **进入前端目录**：
   ```bash
   cd 你的项目路径/frontend
   ```
3. **安装依赖**：
   ```bash
   npm install
   ```
4. **设置后端地址并启动**：
   ```bash
   # 将 192.168.1.100 替换为你的 Windows 机器实际 IP
   set VITE_BACKEND_PROXY_TARGET=http://192.168.1.100:8000
   npm run dev
   ```

   **Mac/Linux 用户**：
   ```bash
   VITE_BACKEND_PROXY_TARGET=http://192.168.1.100:8000 npm run dev
   ```

5. **验证前端服务**：
   打开浏览器访问 `http://localhost:5173`

## 4. 演示操作

### 4.1 准备演示数据

1. **在 Windows 机器上准备图片文件夹**
   - 例如：`C:\demo_images`
   - 放入一些测试图片（.jpg/.png）

### 4.2 前端操作步骤

1. **打开浏览器**访问 `http://localhost:5173`
2. **上传图片**：
   - 点击"上传图片"按钮
   - 选择测试图片上传
3. **建库操作**：
   - 点击"建库"菜单
   - 选择"文件夹"类型
   - 输入库名称（如：演示库）
   - 路径填写：`C:\demo_images`（Windows 机器上的实际路径）
   - 点击"开始建库"
4. **检索操作**：
   - 点击"检索"菜单
   - 上传查询图片
   - 选择已建好的库
   - 点击"开始检索"

## 5. 常见问题解决

### 5.1 前端无法连接后端

**症状**：前端页面空白或报错
**解决**：
1. 检查 Windows 机器 IP 是否正确
2. 确保后端服务已启动
3. 检查防火墙设置：
   ```cmd
   netsh advfirewall firewall add rule name="Backend API" dir=in action=allow protocol=TCP localport=8000
   ```

### 5.2 算法服务启动失败

**症状**：算法服务报错
**解决**：
1. 检查模型路径是否正确
2. 确保模型文件存在
3. 查看详细日志：
   ```cmd
   set PYTHONUNBUFFERED=1
   python launcher/run_all.py
   ```

### 5.3 建库时找不到文件

**症状**：建库失败，提示文件不存在
**解决**：
1. 确保 `MMR_DEMO_MODE=true` 已设置
2. 检查路径格式（Windows 使用 `\`，前端填写时使用 `/`）
3. 确保文件确实存在于 Windows 机器上

## 6. 快速检查清单

- [ ] Windows 机器：算法服务运行在 `18080-18083` 端口
- [ ] Windows 机器：后端服务运行在 `8000` 端口
- [ ] Windows 机器：防火墙已开放相关端口
- [ ] 教室电脑：前端服务运行在 `5173` 端口
- [ ] 教室电脑：能访问 `http://Windows_IP:8000/api/v1/health`
- [ ] 演示数据已准备好

## 7. 一键启动脚本（可选）

### Windows 机器启动脚本

创建 `start_services.bat`：
```batch
@echo off
echo 启动算法服务...
cd algorithm
start cmd /k "set I2I_CKPT_PATH=你的模型路径\i2i & set T2I_CKPT_PATH=你的模型路径\t2i & set T2V_CKPT_PATH=你的模型路径\t2v & set MMR_GATEWAY_HOST=0.0.0.0 & set MMR_GATEWAY_PORT=18080 & python launcher/run_all.py"

echo 启动后端服务...
cd backend
start cmd /k "set MMR_ALGORITHM_MODE=http & set MMR_ALGORITHM_GATEWAY_URL=http://127.0.0.1:18080 & set MMR_ALGORITHM_TIMEOUT=600 & set MMR_DEMO_MODE=true & uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo 服务已启动！
pause
```

### 教室电脑启动脚本

创建 `start_frontend.bat`：
```batch
@echo off
set /p IP="请输入Windows机器IP地址: "
cd frontend
set VITE_BACKEND_PROXY_TARGET=http://%IP%:8000
echo 正在启动前端服务...
npm run dev
pause
```

## 8. 技术支持

如遇到问题：
1. 检查各服务日志
2. 确认网络连通性（ping Windows_IP）
3. 查看防火墙设置
4. 联系技术支持人员