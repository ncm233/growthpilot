# 部署（Zeabur）

## 为什么是 Zeabur

无 Docker 硬约束下最省事的选择：中国网络访问友好、支持 Python（Nixpacks 自动识别）、
免费额度够跑一个 Demo 级别的服务。见 [TECH_STACK.md](TECH_STACK.md) 的选型记录。

## 服务配置

| 项 | 值 |
|---|---|
| Root Directory | `apps/agent-service` |
| Start Command | 读 `Procfile`：`uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Python 版本 | 3.11（`.python-version` 文件已锁定，lancedb/pyarrow 是版本相关的预编译 wheel，不能随便让平台选最新版） |
| 依赖安装 | `requirements.txt`（已含 lancedb/tantivy/jieba/langfuse，见文件注释） |

## 环境变量

跟本地 `.env` 一一对应，在 Zeabur 项目的 Variables 面板里配置：

```
LLM_PROVIDER=mock                    # 建议保持 mock：免费、零延迟、确定性叙述；
                                      # 要接真实 LLM 才需要下面三行
# LLM_BASE_URL=
# LLM_API_KEY=
# LLM_MODEL=deepseek-chat

EMBEDDER_PROVIDER=siliconflow        # 建议设为真实模式，这是项目要展示的核心能力
RERANKER_PROVIDER=siliconflow
SILICONFLOW_API_KEY=<你的key>
SILICONFLOW_EMBEDDING_MODEL=BAAI/bge-m3
SILICONFLOW_RERANK_MODEL=BAAI/bge-reranker-v2-m3

LANGFUSE_PUBLIC_KEY=<你的key>        # 可选，但强烈建议配上——面试官能看到真实 trace
LANGFUSE_SECRET_KEY=<你的key>
LANGFUSE_BASE_URL=<你注册时的区域地址>

# 飞书/企业微信留空即可，走 Mock 实现，Dashboard 上审批按钮照常能点
```

**为什么 `LLM_PROVIDER` 建议保持 `mock`，而 `EMBEDDER_PROVIDER`/`RERANKER_PROVIDER` 建议用真实模式**：
项目要展示的核心工程能力是 RAG 检索（embedding/rerank quality），MockLLM 的模板化叙述已经足够
让整条链路可读、可演示，且零成本零延迟；换成真实 LLM 只是让文字更"自然"，边际价值不如把
SiliconFlow 的真实检索效果亮出来。如果想要更好的叙述效果，可以自己加 DeepSeek key，成本很低
（~¥0.01-0.03/次请求，见 [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md)）。

## 部署前自检（本地已验证过的行为，部署后要复测一遍）

- [ ] `app/main.py` 的 startup 事件会自动跑 `ingest.main()` 建 LanceDB 索引——**本地用一个全新
      `data/lancedb` 目录测过，8 条种子案例能正确入库**，但没有在真实 Zeabur 容器里验证过路径解析
      是否一致（容器内文件系统结构如果跟本地 `cd apps/agent-service` 跑起来不完全一样，
      `store.py`/`main.py` 里那几个 `os.path.dirname(...)` 相对路径计算可能会跑偏）——
      **这是唯一没有 100% 把握的部分，部署后第一件事就是测 `/api/corpus` 和 `/api/run` 里
      有没有 citations**
- [ ] `growthpilot.db`（SQLite）是容器本地文件，**没配持久化卷，每次重新部署数据会清空**——
      对一个 Demo 项目这是可接受的，展示的是"系统能跑通"而不是"历史数据不丢失"，
      面试时可以主动说清楚这个取舍
- [ ] 确认 `/` 首页、`/api/run`、`/api/corpus` 三个端点部署后都能正常访问

## 已知限制（诚实写出来，别等面试官问）

- 单实例，无横向扩展；SQLite 单机、无并发写——见 [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md) 决策 #8
- 没有配持久化存储，每次重新部署 `runs`/`memory` 表清空，LanceDB 索引会在 startup 时重建（幂等，不是 bug）
- MCP Server（`apps/mcp-server/`）**没有部署**——它是给本地 Claude Desktop 连的工具，
  部署一个公网可访问的 MCP Server 涉及额外的鉴权设计（谁能调用 `propose_experiment`），
  超出了这个 Demo 的范围，面试时可以说明这是刻意的范围控制而不是漏掉了
