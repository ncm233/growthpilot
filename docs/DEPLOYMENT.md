# 部署（Render，不是最初计划的 Zeabur）

**已上线并实测验证：[growthpilot-6zl2.onrender.com](https://growthpilot-6zl2.onrender.com)**

## 为什么中途从 Zeabur 换成了 Render

[TECH_STACK.md](TECH_STACK.md) 里最初选型是 Zeabur，理由是"中国网络访问友好 + 免费额度够用"。
**真去部署的时候发现这个判断已经过时了**：Zeabur 在这份文档写完之后把共享区域的免费 PaaS 部署
整个下线了，现在 `zeabur project create` 会直接报错：

```
Shared clusters are deprecated. Please rent a Server and use server-XXXXXXXX as the region code.
```

也就是说现在必须先在 Zeabur 上**租一台 Dedicated Server**（最便宜的选项实测是腾讯云新加坡区，
2 核 2G，$3/月）才能部署，不再有免费选项。这不是我最初判断错了——是平台商业模式在这份文档写完
之后变了。**真去操作才发现这个变化，而不是继续依赖一份几周前写的选型文档，这个过程本身就值得记录。**

比较了几个平台的当前真实条款（不是凭旧印象，逐个搜索验证过）：

| 平台 | 免费层现状 | 是否要绑卡 |
|---|---|---|
| Zeabur | ❌ 已下线，现在最低 $3/月起 | 需要 |
| Railway | 仅 30 天 $5 一次性试用，之后要付费 | 不需要（但试用期后要收费） |
| Hugging Face Spaces | CPU 免费层真免费，但**跑 Docker Space 现在需要付费**——我们这个项目是 FastAPI（Docker 风格部署），不适用 | 不需要 |
| **Render** | ✅ **真免费**，750 小时/月 Web Service 额度，无需信用卡 | **不需要** |

最终选 Render。代价：免费层 15 分钟无请求会休眠，下次访问要等 30-60 秒冷启动——
面试演示前记得先访问一次热身。

## 部署方式：`render.yaml` Blueprint

Render 没有像 Zeabur 那样能被第三方 CLI 完全自动化操作的接口，走的是**基础设施即代码**：
仓库根目录的 [`render.yaml`](../render.yaml) 定义好服务配置，在 Render 网页上连一次 GitHub 账号、
选这个仓库、点 "New Blueprint"，Render 读取 `render.yaml` 自动建服务，不用在网页上手动一项项填。

### 你需要做的（这几步必须是你本人操作，涉及账号授权）

1. 打开 [dashboard.render.com](https://dashboard.render.com)，用 GitHub 账号登录（免费，不用绑卡）
2. 右上角 "New +" → "Blueprint"
3. 选择 `ncm233/growthpilot` 这个仓库，Render 会自动检测到根目录的 `render.yaml`
4. 会提示你填 4 个标了 `sync: false` 的密钥（`render.yaml` 里故意没写死，密钥不会进 git）：
   - `SILICONFLOW_API_KEY`
   - `LANGFUSE_PUBLIC_KEY`
   - `LANGFUSE_SECRET_KEY`
   - `LANGFUSE_BASE_URL`
5. 确认创建，Render 会自动跑 `pip install -r requirements.txt` 然后启动服务

### `render.yaml` 里已经配好的

| 项 | 值 |
|---|---|
| 服务类型 | `type: web`, `runtime: python`, `plan: free` |
| 区域 | `singapore`（离中国最近的免费区域选项） |
| Root Directory | `apps/agent-service`（monorepo，只用这个子目录） |
| 启动命令 | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Python 版本 | 3.11.9（跟 `.python-version` 一致，lancedb/pyarrow 是版本相关的预编译 wheel） |
| `LLM_PROVIDER` | `mock`（免费零延迟，见下方说明） |
| `EMBEDDER_PROVIDER` / `RERANKER_PROVIDER` | `siliconflow`（真实检索能力，这是项目要展示的核心） |

**为什么 `LLM_PROVIDER` 保持 `mock`，而 `EMBEDDER_PROVIDER`/`RERANKER_PROVIDER` 用真实模式**：
项目要展示的核心工程能力是 RAG 检索，MockLLM 的模板化叙述已经足够让整条链路可读、可演示，
且零成本零延迟；换成真实 LLM 只是让文字更"自然"，边际价值不如把 SiliconFlow 的真实检索效果亮出来。

## 部署后实测结果（已验证，不是自检清单了）

真实部署到 `https://growthpilot-6zl2.onrender.com` 之后逐项测过：

- [x] **`app/main.py` 的 startup 自动 ingest 在 Render 容器里正常工作**——`rootDir: apps/agent-service`
      配置下，相对路径解析跟本地一致，`/api/corpus` 返回真实 8 条语料，之前"没有 100% 把握"的地方
      现在confirmed 没问题
- [x] **`/api/run` 端到端测过**：真实调用 SiliconFlow API，`opportunity.citations` 返回 3 条案例，
      top1 score 0.88+，跟本地测试的检索质量一致
- [x] **Langfuse trace 从生产环境正确上报**：生产请求的 trace 落到了跟本地开发/MCP Server 同一个
      Langfuse 项目里，三个入口共用一套可观测性
- [x] `growthpilot.db`（SQLite）是容器本地文件，没配持久化卷，每次重新部署数据会清空——
      对一个 Demo 项目是可接受的取舍
- [ ] 免费层容器 15 分钟无请求会休眠，**面试前务必先访问一次热身**，冷启动 30-60 秒（这条没法提前验证，
      是长期要记住的使用注意事项）

## 已知限制（诚实写出来，别等面试官问）

- 单实例，无横向扩展；SQLite 单机、无并发写——见 [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md) 决策 #8
- 没有配持久化存储，每次重新部署 `runs`/`memory` 表清空，LanceDB 索引会在 startup 时重建（幂等，不是 bug）
- 免费层会休眠，不是生产级可用性——面试可以直接说"这是 Demo 级部署，生产化第一件事就是升级付费层去掉休眠"
- MCP Server（`apps/mcp-server/`）**没有部署**——它是给本地 Claude Desktop 连的工具，
  部署一个公网可访问的 MCP Server 涉及额外的鉴权设计（谁能调用 `propose_experiment`），
  超出了这个 Demo 的范围，面试时可以说明这是刻意的范围控制而不是漏掉了

## 面试话术：怎么讲这次平台切换

> 「我最初技术选型定的是 Zeabur，理由是中国网络友好、免费额度够用。真去部署的时候发现
> Zeabur 已经把免费共享部署下线了，现在必须先租服务器，最低也要 $3/月。我没有直接掏钱了事，
> 而是重新调研了几个平台当前真实的免费层条款——不是凭记忆，是逐个去查最新文档——发现
> Hugging Face Spaces 的免费 CPU 层虽然免费，但跑 Docker 类型的服务现在需要付费，不适合我们这个
> FastAPI 项目；Railway 只有一次性 30 天试用；最后选了 Render，真免费、不用绑卡，代价是有冷启动。
> 这个过程我觉得比选型本身更值得讲——技术选型文档会过时，平台条款会变，得在真正要用的时候
> 重新验证一遍，不能一直依赖几周前写好的结论。」
