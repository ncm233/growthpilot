# growthpilot-mcp

把 GrowthPilot 的检索层和增长实验生成能力，暴露成标准 MCP（Model Context Protocol）工具，
任何 MCP 客户端（Claude Desktop、Cursor、Claude Code 等）都能直接调用。

## 暴露了什么，故意没暴露什么

| 工具 | 做什么 | 只读/生成 |
|---|---|---|
| `search_growth_playbook(query, top_k=3)` | 检索增长案例知识库（RAG），返回带引用的历史 A/B 案例 | 只读 |
| `fetch_growth_data(metric_name)` | 拉取转化漏斗、表单字段、CRM 分群、ERP 订单快照 | 只读 |
| `propose_experiment(goal, budget_limit)` | 生成一份带引用的 A/B 实验方案，写入待审批队列 | 生成，**不写回** |
| `get_experiment_status(run_id)` | 查询某次提案的审批状态 | 只读 |

**`decide`/审批动作刻意没有做成 MCP 工具。** 让任何 MCP 客户端（包括调用它的 LLM）能一句话
批准/拒绝并触发真实写回，会直接违反 GrowthPilot 的核心设计——审批必须由人类在 Dashboard
上完成。这条线不能被 MCP 绕过，即使代价是这个 MCP Server 看起来"能力更少"。

## 为什么是独立 venv，而不是复用 agent-service 的

`fastmcp`（背后的 `mcp` SDK）需要的 `starlette`/`uvicorn` 版本区间，跟 agent-service 锁定的
`fastapi==0.115.0` 要求的 `starlette<0.39.0` 直接冲突——**装到同一个 venv 里会当场把 FastAPI
服务弄坏**（实测复现过，见 git log）。两边各自独立 venv 是唯一干净的做法，`_bootstrap.py` 用
`sys.path` 让这个包能直接 `import app.*`，不需要正式把 agent-service 打包安装。

## 为什么是 HTTP transport，不是 STDIO

MCP Server 教程/模板默认多半是 STDIO。这里改成 HTTP 不是风格选择，是**实测出来的**：
任何调用 LanceDB（Rust/tokio 后端）的工具，在 FastMCP 的 STDIO transport 下会**永久挂死**
（真实子进程 + 真实 JSON-RPC 协议测试复现，不是猜的），换成 HTTP transport 后同样的调用
瞬间返回。这跟 MCP Python SDK 仓库里报告过的一类问题吻合（stdio 下某些阻塞调用会挂起，
SSE/HTTP 下完全正常）。HTTP 也正好是 Phase 5 部署到 Zeabur 需要的 transport，不是额外成本。

## 本地运行

```bash
cd apps/mcp-server
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install lancedb==0.15.0 tantivy==0.22.0 jieba==0.42.1
```

启动（默认端口 8210，可用 `GROWTHPILOT_MCP_PORT` 环境变量改）：

```bash
run.bat
```

或不用 bat：

```bash
set PYTHONPATH=src
.venv\Scripts\python.exe -m growthpilot_mcp
```

## 接入 Claude Desktop

Claude Desktop 配置文件（Windows: `%APPDATA%\Claude\claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "growthpilot": {
      "url": "http://127.0.0.1:8210/mcp"
    }
  }
}
```

**先手动运行 `run.bat` 把服务器跑起来，再重启 Claude Desktop**（HTTP transport 下，
Claude Desktop 是连接到一个已经在跑的服务，不会像 STDIO 那样自动帮你拉起子进程）。

## 依赖 `.env`

工具运行时会读 `apps/agent-service/.env`（`app.config` 的 `load_dotenv()` 从它自己所在
文件位置向上找，跟这个包自己的工作目录无关），所以只要 agent-service 那边配好了
`SILICONFLOW_API_KEY` 等密钥，这里不用重复配置。
