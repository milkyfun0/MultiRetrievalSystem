默认算法模式已改为 http。

关键修改:
- app/core/config.py: `algorithm_mode: str = "http"`

说明:
- 后端默认通过 `MMR_ALGORITHM_GATEWAY_URL` 调用真实算法网关
- 默认网关地址仍为 `http://127.0.0.1:18080`
- 如需覆盖, 可设置环境变量 `MMR_ALGORITHM_MODE` 和 `MMR_ALGORITHM_GATEWAY_URL`
