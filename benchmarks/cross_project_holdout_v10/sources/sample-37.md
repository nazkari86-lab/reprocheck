# he-wiki-rag

> 基于章节树（Chapter Tree）的个人/团队知识库 RAG 检索系统 + Agent Harness
> 端到端流水线：Markdown 知识库 → 章节树解析 → 向量+BM25 混合检索 → Rerank → LLM 回答

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)]()
[![Node](https://img.shields.io/badge/Node-18+-green.svg)]()

## ✨ 特性

- 🧠 **章节树索引**：保留 Markdown 文档的层级语义（父/子/兄弟节点 + 面包屑），告别"傻切块"
- 🔍 **三阶段混合检索**：BGE-M3 向量召回 + jieba BM25 关键词召回 + Cross-Encoder Rerank
- 🌐 **自动查询扩展**：基于 Embedding 相似度自动发现中英同义词，零维护同义词表
- 🤖 **Agent Harness CLI**：流式对话、工具调用、状态持久化、Trace 记录一把梭
- 📊 **内置评测体系**：Recall@K / NDCG / MRR / Hit Rate，离线对比不同检索策略

## 🏗 架构一览

```
   ┌──────────────────┐         ┌──────────────────────┐
   │  he-harness      │  HTTP   │  he-rag-engine       │
   │  (Node.js CLI)   │ ──────▶ │  (FastAPI + Chroma)  │
   │  Agent Loop      │         │  Hybrid Search       │
   │  Tool Guardrail  │         │  + Rerank            │
   └──────────────────┘         └──────────┬───────────┘
                                            │
                                            ▼
                                  ┌──────────────────┐
                                  │  wiki/           │
                                  │  Markdown 知识库  │
                                  │  + chapter_trees │
                                  └──────────────────┘
```

更详细的架构图、字段说明、API 文档见：

- 📘 [RAG 检索引擎文档](he-rag-engine/README.md)
- 📗 [Agent Harness 文档](he-harness/README.md)

## 🎬 演示

**RAG 知识库问答 CLI**：在终端用自然语言提问，Agent 自动调用 `knowledge_search` 工具检索知识库，结合检索结果生成带引用的回答。

![RAG 问答 CLI 演示](assets/demo-rag-chat.png)

**检索结果**（Hybrid + Rerank）：返回与查询相关的章节，附带面包屑路径、原文摘要、相关度分数。

![检索结果演示](assets/demo-search-results.png)

## 📦 目录结构

```
he-wiki-rag/
├── he-rag-engine/        # Python FastAPI 检索后端（向量 + BM25 + Rerank）
├── he-harness/           # Node.js Agent Harness（CLI 交互 + 工具调用）
├── wiki/                 # 示例知识库（Markdown + 章节树索引）
├── start.sh              # 一键启动脚本
├── README.md             # 本文件
├── LICENSE               # MIT 协议
└── .gitignore
```

## 🚀 快速开始（5 分钟跑起来）

### 0. 环境要求

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | ≥ 3.11 | 运行 RAG Engine |
| Node.js | ≥ 18 | 运行 Harness CLI |
| SiliconFlow API Key | - | Embedding / Rerank / LLM（[申请地址](https://cloud.siliconflow.cn/i/26lIrpg0)） |
| Ollama（可选） | - | 本地 Embedding / Rerank fallback |

> 也可以用 OpenAI、Anthropic 等任何 OpenAI 兼容 API 替换 LLM 提供方。

### 1. 克隆仓库

```bash
git clone https://github.com/你的用户名/he-wiki-rag.git
cd he-wiki-rag
```

### 2. 配置环境变量

```bash
# RAG Engine 配置（必填：API Key）
cp he-rag-engine/.env.example he-rag-engine/.env
# 编辑 he-rag-engine/.env 填入你的 RAG_SILICONFLOW_API_KEY

# Harness CLI 配置（可选：默认使用 Mock LLM 体验）
cp he-harness/.env.example he-harness/.env
# 编辑 he-harness/.env 选择 LLM_PROVIDER 并填入对应 Key
```

### 3. 一键启动（推荐）

```bash
./start.sh
```

脚本会自动：

1. 创建 Python 虚拟环境并安装 RAG Engine 依赖
2. 后台启动 FastAPI 服务（`http://localhost:8000`）
3. 安装 Harness 的 npm 依赖
4. 前台启动 RAG 问答 CLI

> ⚠️ **首次启动 RAG Engine 会自动构建向量索引**，需要调用 Embedding API，请确保 `.env` 已配好 key。

### 4. 手动分步启动（适合二次开发）

```bash
# 终端 A —— RAG Engine
cd he-rag-engine
python -m venv venv && source venv/bin/activate
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 终端 B —— Harness CLI
cd he-harness
npm install
npm run rag-chat
```

启动后即可在 CLI 中提问，例如：

```
你: RAG 的切块策略有哪些？
🔎 正在检索知识库...
✅ 知识库助手：……（引用了 3 个章节，附带面包屑路径）
```

## ⚙️ 关键配置项

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `RAG_SILICONFLOW_API_KEY` | SiliconFlow API Key | 必填 |
| `RAG_EMBEDDING_PROVIDER` | Embedding 提供方（siliconflow / ollama） | siliconflow |
| `RAG_RERANK_PROVIDER` | Rerank 提供方（siliconflow / ollama） | siliconflow |
| `RAG_KB_ROOT` | 知识库根目录 | `./wiki` |
| `RAG_EXPAND_SIMILARITY_THRESHOLD` | 自动查询扩展相似度阈值 | `0.75` |
| `LLM_PROVIDER` (Harness) | Harness LLM 提供方（openai / ollama / mock） | mock |

完整配置见 [`.env.example` 文件](he-rag-engine/.env.example)。

## 🧪 评测

```bash
cd he-rag-engine
python evaluate.py
```

支持评测 Recall@K、Precision@K、MRR、NDCG@K、Hit Rate@K，按难度和分类拆分。

## 🛠 常见问题

<details>
<summary><b>Q：首次启动很慢？</b></summary>

A：首次启动会调用 Embedding API 构建向量索引。如果你的知识库较大（> 1000 文档），可能需要几分钟。后续启动秒级。

</details>

<details>
<summary><b>Q：可以替换成自己的 LLM 吗？</b></summary>

A：可以。`he-harness` 通过 OpenAI 兼容协议对接 LLM，只需修改 `.env` 中的 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY` 即可指向任何 OpenAI 兼容服务（Azure OpenAI、vLLM、Ollama、DeepSeek 等）。

</details>

<details>
<summary><b>Q：wiki/ 目录里的内容是？</b></summary>

A：是仓库自带的一份**示例知识库**（约 70 篇 RAG / 知识工程相关的 Markdown），用于让你 clone 下来就能直接跑通。你也可以清空 `wiki/` 然后放入自己的内容。

</details>

<details>
<summary><b>Q：如何接入自己的知识库？</b></summary>

A：把你的 Markdown 知识库放到 `wiki/` 目录下，然后运行仓库提供的章节树构建工具（详见 [知识库构建流程](he-rag-engine/README.md)）生成 `wiki/indices/chapter_trees.json`，最后 `POST /admin/rebuild-index` 即可热更新索引。

</details>

## 🛣 路线图

- [ ] Wiki 前端编辑器（所见即所得）
- [ ] 多租户 / 多人协作
- [ ] Rerank 蒸馏到本地小模型
- [ ] 支持 PDF / Notion 导入

## 🤝 贡献

欢迎 PR！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)（如未提供可先略过）。

## 📄 协议

[MIT](LICENSE) © 2026
