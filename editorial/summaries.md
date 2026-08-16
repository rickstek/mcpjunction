# Editorial summaries

Human-written summaries, one per server. This file is the source of truth:
`scripts/pipeline.py` reads it on every nightly run and copies each entry into
the dataset's `editorial_summary` field. Automation only ever READS this file —
nothing writes into it. Deleting an entry here removes it from the site on the
next run.

## Format

One `##` heading per server, containing the server id exactly as it appears in
the URL (`owner--repo`, lowercase, double hyphen). Everything until the next
heading is the summary. Line breaks inside an entry are fine — they get folded
into one paragraph.

Only headings containing `--` are read as entries, which is why these
documentation headings, and the `# category` headings below, are ignored.
Entries may appear in any order; they are grouped by category here because
that is the easiest way to write them.

A heading with nothing written under it publishes nothing, so the unwritten
entries below are a safe work queue. The reference block under each heading is
an HTML comment and is stripped before parsing — leave it or delete it.

## House style

- 40–80 words. Say what it does, who it's for, and one thing that
  distinguishes it. A caveat is welcome when it's true and useful.
- Your own words. Never paraphrase the GitHub description — that text already
  appears on the page, attributed to the repo, and duplicating it defeats the
  purpose of writing these.
- No superlatives, no "best", no marketing voice. This directory's credibility
  is the product.
- No facts that go stale: no star counts, version numbers, or dates. The
  dataset already carries those and renders them live.
- Never imply endorsement or security review. The reviewed badge is set only
  by manual review, and this field must not read like one.

Priority: the first two entries in each category are the highest value — they
put unique prose on every category page. The third is a stretch goal.

---

# Browser Automation  (browser-automation)

## d4vinci--scrapling

<!--
  D4Vinci/Scrapling  ·  Python  ·  74,002 stars  ·  BSD-3-Clause
  https://github.com/D4Vinci/Scrapling
  page: https://mcpjunction.ai/servers/d4vinci--scrapling
  install hint: pip install scrapling
  GitHub says: 🕷️ An adaptive Web Scraping framework that handles everything from a single request to a full-scale crawl!
-->


## chromedevtools--chrome-devtools-mcp

<!--
  ChromeDevTools/chrome-devtools-mcp  ·  TypeScript  ·  49,180 stars  ·  Apache-2.0
  https://github.com/ChromeDevTools/chrome-devtools-mcp
  page: https://mcpjunction.ai/servers/chromedevtools--chrome-devtools-mcp
  install hint: npx chrome-devtools-mcp
  GitHub says: Chrome DevTools for coding agents
-->
Drives a real Chrome instance from a coding agent — navigate, inspect the DOM, and read performance and load traces instead of guessing from static HTML. Targets elements through accessibility-tree snapshots rather than CSS selectors, which is why it holds up on dynamic pages where selector-based automation gets flaky. Comes from the Chrome DevTools team itself, and setup is a single npx command.

## heygen-com--hyperframes

<!--
  heygen-com/hyperframes  ·  TypeScript  ·  40,990 stars  ·  Apache-2.0
  https://github.com/heygen-com/hyperframes
  page: https://mcpjunction.ai/servers/heygen-com--hyperframes
  install hint: npx hyperframes
  GitHub says: Write HTML. Render video. Built for agents.
-->
Renders HTML and media into MP4 from an agent, so a workflow that produces data can end with a finished video rather than a file someone still has to edit. Handles product and explainer videos, music-to-video, PR-to-video, even talking-head output. The case where it earns its place is turning structured data into something a non-technical audience will actually sit through.

## snailclimb--javaguide

<!--
  Snailclimb/JavaGuide  ·  JavaScript  ·  157,761 stars  ·  Apache-2.0
  https://github.com/Snailclimb/JavaGuide
  page: https://mcpjunction.ai/servers/snailclimb--javaguide
  install hint: npx javaguide
  GitHub says: Java 面试 & 后端通用面试指南，覆盖计算机基础、数据库、分布式、高并发、系统设计与 AI 应用开发
-->


## graphify-labs--graphify

<!--
  Graphify-Labs/graphify  ·  Python  ·  106,404 stars  ·  Apache-2.0
  https://github.com/Graphify-Labs/graphify
  page: https://mcpjunction.ai/servers/graphify-labs--graphify
  install hint: pip install graphify
  GitHub says: Turn any codebase, with its docs, SQL schemas, configs, and PDFs, into a queryable knowledge graph. A /graphify skill for Claude Code, Cursor, Codex, and Gemini CLI: local deterministic AST parsing, every edge explained, no vector store.
-->


## netdata--netdata

<!--
  netdata/netdata  ·  Go  ·  80,183 stars  ·  GPL-3.0
  https://github.com/netdata/netdata
  page: https://mcpjunction.ai/servers/netdata--netdata
  install hint: go install github.com/netdata/netdata@latest
  GitHub says: The fastest path to AI-powered full stack observability, even for lean teams.
-->



# Communication  (communication)

## langgenius--dify

<!--
  langgenius/dify  ·  TypeScript  ·  152,447 stars  ·  NOASSERTION
  https://github.com/langgenius/dify
  page: https://mcpjunction.ai/servers/langgenius--dify
  install hint: npx dify
  GitHub says: Build Agentic workflows, RAG pipelines, with rich AI model and tool support on one collaborative workspace. Deploy on cloud, VPC, or self-hosted, so teams move from prototype to production without rebuilding the stack.
-->


## sansan0--trendradar

<!--
  sansan0/TrendRadar  ·  Python  ·  61,468 stars  ·  GPL-3.0
  https://github.com/sansan0/TrendRadar
  page: https://mcpjunction.ai/servers/sansan0--trendradar
  install hint: pip install trendradar
  GitHub says: ⭐AI-driven public opinion & trend monitor with multi-platform aggregation, RSS, and smart alerts.🎯 告别信息过载，你的 AI 舆情监控助手与热点筛选工具！聚合多平台热点 +  RSS 订阅，支持关键词精准筛选。AI 智能筛选新闻 + AI 翻译 +  AI 分析简报直推手机，也支持接入 MCP 架构，赋能 AI 自然语言对话分析、情感洞察与趋势预测等。支持 Docker ，数据本地/云端自持。集成微信/飞书/钉钉/Telegram/邮件/ntfy/bark/slack 等渠道智能推送。
-->


## hkuds--nanobot

<!--
  HKUDS/nanobot  ·  Python  ·  47,004 stars  ·  MIT
  https://github.com/HKUDS/nanobot
  page: https://mcpjunction.ai/servers/hkuds--nanobot
  install hint: pip install nanobot
  GitHub says: Ultra-lightweight, open-source, self-hosted personal AI agent framework in Python with WebUI, tools, memory, MCP, multi-agent workflows, automation, and chat apps
-->



# Finance & Commerce  (finance)

## hkuds--vibe-trading

<!--
  HKUDS/Vibe-Trading  ·  Python  ·  30,865 stars  ·  MIT
  https://github.com/HKUDS/Vibe-Trading
  page: https://mcpjunction.ai/servers/hkuds--vibe-trading
  install hint: uvx vibe-trading
  GitHub says: "Vibe-Trading: Your Personal Trading Agent"
-->
An open-source multi-agent framework for trading research, where separate AI personas take on jobs like macro analysis and crypto research and hand off between each other. Ships with exposure caps and other safety controls, which is more than most agent-trading projects bother with. Documentation and update cadence are both solid. Nothing here is financial advice — verify independently before risking capital.

## xbtlin--ai-berkshire

<!--
  xbtlin/ai-berkshire  ·  Python  ·  15,539 stars  ·  MIT
  https://github.com/xbtlin/ai-berkshire
  page: https://mcpjunction.ai/servers/xbtlin--ai-berkshire
  install hint: uvx ai-berkshire
  GitHub says: AI 时代的伯克希尔：基于 Claude Code / Codex 的价值投资研究框架。巴菲特·芒格·段永平·李录四大师方法论 + 多Agent并行研究。| AI-era Berkshire: a value investing research framework built for Claude Code / Codex. 4 masters' methodologies + multi-agent adversarial analysis.
-->


## valuecell-ai--valuecell

<!--
  ValueCell-ai/valuecell  ·  Python  ·  10,998 stars  ·  Apache-2.0
  https://github.com/ValueCell-ai/valuecell
  page: https://mcpjunction.ai/servers/valuecell-ai--valuecell
  install hint: pip install valuecell
  GitHub says: ValueCell is a community-driven, multi-agent platform for financial applications.
-->



# Storage & Files  (storage)

## siyuan-note--siyuan

<!--
  siyuan-note/siyuan  ·  TypeScript  ·  45,804 stars  ·  AGPL-3.0
  https://github.com/siyuan-note/siyuan
  page: https://mcpjunction.ai/servers/siyuan-note--siyuan
  install hint: npx siyuan
  GitHub says: An open-source, privacy-first, self-hosted knowledge workspace where humans and AI agents work together 开源、隐私优先、自托管的知识工作空间，让人与智能体在此协作
-->


## bojieli--ai-agent-book

<!--
  bojieli/ai-agent-book  ·  Python  ·  37,365 stars  ·  Apache-2.0
  https://github.com/bojieli/ai-agent-book
  page: https://mcpjunction.ai/servers/bojieli--ai-agent-book
  install hint: uvx ai-agent-book
  GitHub says: 《深入理解 AI Agent：设计原理与工程实践》（李博杰 著）开源主仓库：全书正文、编译版 PDF 与按章配套代码
-->


## pdfmathtranslate--pdfmathtranslate

<!--
  PDFMathTranslate/PDFMathTranslate  ·  Python  ·  36,164 stars  ·  AGPL-3.0
  https://github.com/PDFMathTranslate/PDFMathTranslate
  page: https://mcpjunction.ai/servers/pdfmathtranslate--pdfmathtranslate
  install hint: pip install pdfmathtranslate
  GitHub says: [EMNLP 2025 Demo] PDF scientific paper translation with preserved formats - 基于 AI 完整保留排版的 PDF 文档全文双语翻译，支持 Google/DeepL/Ollama/OpenAI 等服务，提供 CLI/GUI/MCP/Docker/Zotero
-->



# Design Tools  (design-tools)

## ahujasid--blender-mcp

<!--
  ahujasid/blender-mcp  ·  Python  ·  25,851 stars  ·  MIT
  https://github.com/ahujasid/blender-mcp
  page: https://mcpjunction.ai/servers/ahujasid--blender-mcp
  install hint: uvx blender-mcp
  GitHub says: Community plugin to control Blender 3D with any LLM of your choice
-->


## pascalorg--editor

<!--
  pascalorg/editor  ·  TypeScript  ·  21,385 stars  ·  MIT
  https://github.com/pascalorg/editor
  page: https://mcpjunction.ai/servers/pascalorg--editor
  install hint: npx editor
  GitHub says: Create and share 3D architectural projects.
-->


## udecode--plate

<!--
  udecode/plate  ·  TypeScript  ·  16,492 stars  ·  NOASSERTION
  https://github.com/udecode/plate
  page: https://mcpjunction.ai/servers/udecode--plate
  install hint: npx plate
  GitHub says: Rich-text editor with AI and shadcn/ui
-->
A headless rich-text editor framework on Slate.js and Radix UI, installed through the shadcn/ui CLI so components land in your own codebase instead of behind a dependency. Plugins run from basic formatting through to AI-assisted authoring. That code-ownership model is the reason to choose it over a packaged editor: you keep control of styling and data shape, and you take on the maintenance.

## homeassistant-ai--ha-mcp

<!--
  homeassistant-ai/ha-mcp  ·  Python  ·  4,381 stars  ·  MIT
  https://github.com/homeassistant-ai/ha-mcp
  page: https://mcpjunction.ai/servers/homeassistant-ai--ha-mcp
  install hint: uvx ha-mcp
  GitHub says: The Unofficial and Awesome Home Assistant MCP Server
-->


## martin-ger--esp32_nat_router

<!--
  martin-ger/esp32_nat_router  ·  C  ·  2,091 stars  ·  no license
  https://github.com/martin-ger/esp32_nat_router
  page: https://mcpjunction.ai/servers/martin-ger--esp32_nat_router
  install hint: none
  GitHub says: An AI-enabled NAT Router/Firewall for the ESP32
-->


## mihai-dinculescu--tapo

<!--
  mihai-dinculescu/tapo  ·  Rust  ·  788 stars  ·  MIT
  https://github.com/mihai-dinculescu/tapo
  page: https://mcpjunction.ai/servers/mihai-dinculescu--tapo
  install hint: cargo install tapo
  GitHub says: 🦀 Rust API, 🐍 Python API, and 🤖 MCP Server for TP-Link Tapo smart devices
-->



# IoT, Hardware & Robotics  (iot-hardware)

## mudler--localai

<!--
  mudler/LocalAI  ·  Go  ·  48,467 stars  ·  MIT
  https://github.com/mudler/LocalAI
  page: https://mcpjunction.ai/servers/mudler--localai
  install hint: go install github.com/mudler/LocalAI@latest
  GitHub says: LocalAI is the open-source AI engine. Run any model - LLMs, vision, voice, image, video - on any hardware. No GPU required.
-->


## 78--xiaozhi-esp32

<!--
  78/xiaozhi-esp32  ·  C++  ·  28,901 stars  ·  MIT
  https://github.com/78/xiaozhi-esp32
  page: https://mcpjunction.ai/servers/78--xiaozhi-esp32
  install hint: none
  GitHub says: An MCP-based chatbot | 一个基于MCP的聊天机器人
-->
Have an ESP32-S3 lying around? This turns it into a real-time, cloud-connected voice chatbot, talking to LLMs over WebSocket or MQTT+UDP. The Opus codec keeps latency low enough for genuine back-and-forth conversation, with offline wake-word, echo cancellation and speaker recognition handled on the device. The interesting part is GPIO control: the same agent that answers you can drive screens and actuators.

## xinnan-tech--xiaozhi-esp32-server

<!--
  xinnan-tech/xiaozhi-esp32-server  ·  JavaScript  ·  10,322 stars  ·  MIT
  https://github.com/xinnan-tech/xiaozhi-esp32-server
  page: https://mcpjunction.ai/servers/xinnan-tech--xiaozhi-esp32-server
  install hint: npx xiaozhi-esp32-server
  GitHub says: 本项目为xiaozhi-esp32提供后端服务，帮助您快速搭建ESP32设备控制服务器。Backend service for xiaozhi-esp32, helps you quickly build an ESP32 device control server.
-->



# Gaming & Game Dev  (gaming)

## coplaydev--unity-mcp

<!--
  CoplayDev/unity-mcp  ·  C#  ·  13,397 stars  ·  MIT
  https://github.com/CoplayDev/unity-mcp
  page: https://mcpjunction.ai/servers/coplaydev--unity-mcp
  install hint: none
  GitHub says: Unity MCP acts as a bridge between AI assistants and your Unity Editor. Give your LLM tools to manage assets, control scenes, edit scripts, and automate tasks within Unity.
-->


## coding-solo--godot-mcp

<!--
  Coding-Solo/godot-mcp  ·  JavaScript  ·  5,199 stars  ·  MIT
  https://github.com/Coding-Solo/godot-mcp
  page: https://mcpjunction.ai/servers/coding-solo--godot-mcp
  install hint: npx godot-mcp
  GitHub says: MCP server for interfacing with Godot game engine. Provides tools for launching the editor, running projects, and capturing debug output.
-->


## ivanmurzak--unity-mcp

<!--
  IvanMurzak/Unity-MCP  ·  C#  ·  3,893 stars  ·  Apache-2.0
  https://github.com/IvanMurzak/Unity-MCP
  page: https://mcpjunction.ai/servers/ivanmurzak--unity-mcp
  install hint: none
  GitHub says: AI Skills, MCP Tools, and CLI for Unity Engine. Full AI develop and test loop. Use cli for quick setup. Efficient token usage, advanced tools. Any C# method may be turned into a tool by a single line. Works with Claude Code, Gemini, Copilot, Cursor and any other absolutely for free.
-->



# Security  (security)

## affaan-m--ecc

<!--
  affaan-m/ECC  ·  JavaScript  ·  240,163 stars  ·  MIT
  https://github.com/affaan-m/ECC
  page: https://mcpjunction.ai/servers/affaan-m--ecc
  install hint: npx ecc
  GitHub says: The agent harness performance optimization system. Skills, instincts, memory, security, and research-first development for Claude Code, Codex, Opencode, Cursor and beyond.
-->


## composiohq--composio

<!--
  ComposioHQ/composio  ·  TypeScript  ·  29,691 stars  ·  MIT
  https://github.com/ComposioHQ/composio
  page: https://mcpjunction.ai/servers/composiohq--composio
  install hint: npx composio
  GitHub says: Composio powers 1000+ toolkits, tool search, context management, authentication, and a sandboxed workbench to help you build AI agents that turn intent into action.
-->


## mukul975--anthropic-cybersecurity-skills

<!--
  mukul975/Anthropic-Cybersecurity-Skills  ·  Python  ·  27,785 stars  ·  Apache-2.0
  https://github.com/mukul975/Anthropic-Cybersecurity-Skills
  page: https://mcpjunction.ai/servers/mukul975--anthropic-cybersecurity-skills
  install hint: uvx anthropic-cybersecurity-skills
  GitHub says: 817 structured cybersecurity skills for AI agents · Mapped to 6 frameworks: MITRE ATT&CK, NIST CSF 2.0, MITRE ATLAS, D3FEND, NIST AI RMF & MITRE F3 (Fight Fraud) · agentskills.io standard · Works with Claude Code, GitHub Copilot, Codex CLI, Cursor, Gemini CLI & 20+ platforms · 29 security domains · Apache 2.0
-->



# Monitoring & Observability  (monitoring)

## koala73--worldmonitor

<!--
  koala73/worldmonitor  ·  TypeScript  ·  81,901 stars  ·  AGPL-3.0
  https://github.com/koala73/worldmonitor
  page: https://mcpjunction.ai/servers/koala73--worldmonitor
  install hint: npx worldmonitor
  GitHub says: Real-time global intelligence dashboard. AI-powered news aggregation, geopolitical monitoring, and infrastructure tracking in a unified situational awareness interface
-->


## headroomlabs-ai--headroom

<!--
  headroomlabs-ai/headroom  ·  Python  ·  66,377 stars  ·  Apache-2.0
  https://github.com/headroomlabs-ai/headroom
  page: https://mcpjunction.ai/servers/headroomlabs-ai--headroom
  install hint: pip install headroom
  GitHub says: Compress tool outputs, logs, files, and RAG chunks before they reach the LLM. 20% fewer tokens for coding agents, 60-95% fewer tokens for JSON, same answers. Library, proxy, MCP server.
-->


## nirdiamant--agents-towards-production

<!--
  NirDiamant/agents-towards-production  ·  Jupyter Notebook  ·  21,285 stars  ·  NOASSERTION
  https://github.com/NirDiamant/agents-towards-production
  page: https://mcpjunction.ai/servers/nirdiamant--agents-towards-production
  install hint: none
  GitHub says: End-to-end, code-first tutorials for building production-grade GenAI agents. From prototype to enterprise deployment.
-->



# Cloud & DevOps  (cloud-devops)

## panniantong--agent-reach

<!--
  Panniantong/Agent-Reach  ·  Python  ·  71,765 stars  ·  MIT
  https://github.com/Panniantong/Agent-Reach
  page: https://mcpjunction.ai/servers/panniantong--agent-reach
  install hint: uvx agent-reach
  GitHub says: Give your AI agent eyes to see the entire internet. Read & search Twitter, Reddit, YouTube, GitHub, Bilibili, XiaoHongShu — one CLI, zero API fees.
-->


## ruvnet--ruflo

<!--
  ruvnet/ruflo  ·  TypeScript  ·  67,873 stars  ·  MIT
  https://github.com/ruvnet/ruflo
  page: https://mcpjunction.ai/servers/ruvnet--ruflo
  install hint: npx ruflo
  GitHub says: 🌊 The original agent meta-harness. Deploy intelligent multi-player swarms, coordinate autonomous workflows, and build conversational AI systems. Features adaptive memory, self-learning intelligence, RAG integration, and native Claude Code / Codex / Hermes and many more Integrated
-->


## kong--kong

<!--
  Kong/kong  ·  Lua  ·  43,984 stars  ·  Apache-2.0
  https://github.com/Kong/kong
  page: https://mcpjunction.ai/servers/kong--kong
  install hint: none
  GitHub says: 🦍 The API and AI Gateway
-->
Kong Gateway's core source — an API gateway built on NGINX and OpenResty, aimed at cloud-native and Kubernetes deployments across hybrid and multi-cloud setups. Configuration is programmatic through an Admin API, and the plugin architecture covers authentication, rate limiting and traffic transformation. The AI Gateway layer is the part relevant to this directory: it fronts LLM traffic with cost tracking, model routing and security controls.

## open-webui--open-webui

<!--
  open-webui/open-webui  ·  Python  ·  148,811 stars  ·  NOASSERTION
  https://github.com/open-webui/open-webui
  page: https://mcpjunction.ai/servers/open-webui--open-webui
  install hint: uvx open-webui
  GitHub says: User-friendly AI Interface (Supports Ollama, OpenAI API, ...)
-->


## jeecgboot--jeecgboot

<!--
  jeecgboot/JeecgBoot  ·  Java  ·  47,396 stars  ·  Apache-2.0
  https://github.com/jeecgboot/JeecgBoot
  page: https://mcpjunction.ai/servers/jeecgboot--jeecgboot
  install hint: none
  GitHub says: 【低代码迈入v2.0时代，一句话即可生成整个系统】企业级AI低代码平台，一键生成前后端代码甚至整个系统。 AI Skills 一句话画流程、设计表单、生成报表、大屏。内置 AI应用平台涵盖：AI聊天、知识库、流程编排、MCP插件等，兼容主流大模型。引领AI低代码「Skills 生成 → 在线配置 → 代码生成 → 手工合并->AI修改」开发模式，解决 Java 项目 90% 重复工作，提高效率又不失灵活。
-->


## patchy631--ai-engineering-hub

<!--
  patchy631/ai-engineering-hub  ·  Jupyter Notebook  ·  36,997 stars  ·  MIT
  https://github.com/patchy631/ai-engineering-hub
  page: https://mcpjunction.ai/servers/patchy631--ai-engineering-hub
  install hint: none
  GitHub says: In-depth tutorials on LLMs, RAGs and real-world AI agent applications.
-->



# Productivity & Knowledge  (productivity)

## lobehub--lobehub

<!--
  lobehub/lobehub  ·  TypeScript  ·  81,699 stars  ·  NOASSERTION
  https://github.com/lobehub/lobehub
  page: https://mcpjunction.ai/servers/lobehub--lobehub
  install hint: npx lobehub
  GitHub says: 🤯 LobeHub is your Chief Agent Operator, organizing your agents into 7×24 operations by hiring, scheduling, and reporting on your entire AI team.
-->


## upstash--context7

<!--
  upstash/context7  ·  TypeScript  ·  60,759 stars  ·  MIT
  https://github.com/upstash/context7
  page: https://mcpjunction.ai/servers/upstash--context7
  install hint: npx context7
  GitHub says: Context7 Platform –– Up-to-date code documentation for LLMs and AI code editors
-->


## tirth8205--code-review-graph

<!--
  tirth8205/code-review-graph  ·  Python  ·  30,152 stars  ·  MIT
  https://github.com/tirth8205/code-review-graph
  page: https://mcpjunction.ai/servers/tirth8205--code-review-graph
  install hint: uvx code-review-graph
  GitHub says: Local-first code intelligence graph for MCP and CLI. Builds a persistent map of your codebase so AI coding tools read only what matters, with benchmarked context reductions on reviews and large-repo workflows.
-->



# AI Media Generation  (ai-media)

## rohitg00--ai-engineering-from-scratch

<!--
  rohitg00/ai-engineering-from-scratch  ·  Python  ·  46,746 stars  ·  MIT
  https://github.com/rohitg00/ai-engineering-from-scratch
  page: https://mcpjunction.ai/servers/rohitg00--ai-engineering-from-scratch
  install hint: uvx ai-engineering-from-scratch
  GitHub says: Learn it. Build it. Ship it for others.
-->
Over 500 hands-on AI engineering lessons that run entirely locally, so progress persists offline and resumes where you left off. Loads straight into Claude Code, Cursor and other terminal agents via npx skills add, which is unusual for a learning resource — most still assume a browser. Better suited to structured self-teaching than to quick reference.

## mastra-ai--mastra

<!--
  mastra-ai/mastra  ·  TypeScript  ·  27,202 stars  ·  NOASSERTION
  https://github.com/mastra-ai/mastra
  page: https://mcpjunction.ai/servers/mastra-ai--mastra
  install hint: npx mastra
  GitHub says: Mastra is the modern TypeScript framework for AI-powered applications and agents.
-->


## screenpipe--screenpipe

<!--
  screenpipe/screenpipe  ·  Rust  ·  20,959 stars  ·  NOASSERTION
  https://github.com/screenpipe/screenpipe
  page: https://mcpjunction.ai/servers/screenpipe--screenpipe
  install hint: cargo install screenpipe
  GitHub says: YC (S26) | Record your screen 24/7 and plug into your agents. Local, private, secure. Connect to OpenClaw, Hermes agent and 100+ apps
-->



# AI Coding Assistants  (ai-coding)

## farion1231--cc-switch

<!--
  farion1231/cc-switch  ·  Rust  ·  127,285 stars  ·  MIT
  https://github.com/farion1231/cc-switch
  page: https://mcpjunction.ai/servers/farion1231--cc-switch
  install hint: cargo install cc-switch
  GitHub says: A cross-platform desktop All-in-One assistant for Claude Code, Codex, OpenCode, OpenClaw, Grok Build & Hermes Agent. Only official website: ccswitch.io
-->


## composiohq--awesome-claude-skills

<!--
  ComposioHQ/awesome-claude-skills  ·  Python  ·  72,502 stars  ·  no license
  https://github.com/ComposioHQ/awesome-claude-skills
  page: https://mcpjunction.ai/servers/composiohq--awesome-claude-skills
  install hint: uvx awesome-claude-skills
  GitHub says: A curated list of awesome Claude Skills, resources, and tools for customizing Claude AI workflows
-->


## diegosouzapw--omniroute

<!--
  diegosouzapw/OmniRoute  ·  TypeScript  ·  48,058 stars  ·  MIT
  https://github.com/diegosouzapw/OmniRoute
  page: https://mcpjunction.ai/servers/diegosouzapw--omniroute
  install hint: npx omniroute
  GitHub says: Never stop coding. Free MIT AI gateway: one endpoint, 339 providers (90+ free), 1200+ models — Kimi, Claude, GPT, Gemini, GLM, DeepSeek, MiniMax. Works with Claude Code, Codex, Cursor, OpenCode, Cline & Copilot. Quota-aware auto-fallback, RTK+Caveman compression saves 15-95% tokens, MCP/A2A, Desktop/PWA. Built by 450+ contributors
-->



# AI Agents  (ai-agents)

## google-gemini--gemini-cli

<!--
  google-gemini/gemini-cli  ·  TypeScript  ·  106,524 stars  ·  Apache-2.0
  https://github.com/google-gemini/gemini-cli
  page: https://mcpjunction.ai/servers/google-gemini--gemini-cli
  install hint: npx gemini-cli
  GitHub says: An open-source AI agent that brings the power of Gemini directly into your terminal.
-->


## aaif-goose--goose

<!--
  aaif-goose/goose  ·  Rust  ·  52,812 stars  ·  Apache-2.0
  https://github.com/aaif-goose/goose
  page: https://mcpjunction.ai/servers/aaif-goose--goose
  install hint: cargo install goose
  GitHub says: an open source, extensible AI agent that goes beyond code suggestions - install, execute, edit, and test with any LLM
-->


## agentscope-ai--agentscope

<!--
  agentscope-ai/agentscope  ·  Python  ·  28,951 stars  ·  Apache-2.0
  https://github.com/agentscope-ai/agentscope
  page: https://mcpjunction.ai/servers/agentscope-ai--agentscope
  install hint: pip install agentscope
  GitHub says: Build and run agents you can see, understand and trust.
-->



# AI Models & Inference  (ai-models)

## yzfly--awesome-mcp-zh

<!--
  yzfly/Awesome-MCP-ZH  ·  language n/a  ·  7,558 stars  ·  MIT
  https://github.com/yzfly/Awesome-MCP-ZH
  page: https://mcpjunction.ai/servers/yzfly--awesome-mcp-zh
  install hint: none
  GitHub says: MCP 资源精选， MCP指南，Claude MCP，MCP Servers, MCP Clients
-->


## u14app--deep-research

<!--
  u14app/deep-research  ·  JavaScript  ·  4,682 stars  ·  MIT
  https://github.com/u14app/deep-research
  page: https://mcpjunction.ai/servers/u14app--deep-research
  install hint: npx deep-research
  GitHub says: Use any LLMs (Large Language Models) for Deep Research. Support SSE API and MCP server.
-->


## liaokongvfx--mcp-chinese-getting-started-guide

<!--
  liaokongVFX/MCP-Chinese-Getting-Started-Guide  ·  language n/a  ·  3,558 stars  ·  no license
  https://github.com/liaokongVFX/MCP-Chinese-Getting-Started-Guide
  page: https://mcpjunction.ai/servers/liaokongvfx--mcp-chinese-getting-started-guide
  install hint: none
  GitHub says: Model Context Protocol(MCP) 编程极速入门
-->
A step-by-step MCP tutorial written for Chinese-speaking developers, covering custom tool building, stdio transport, and connecting to data sources. Activity has been sparse and the protocol moves quickly, so check the last-pushed date above before relying on any of it.

## n8n-io--n8n

<!--
  n8n-io/n8n  ·  TypeScript  ·  200,640 stars  ·  NOASSERTION
  https://github.com/n8n-io/n8n
  page: https://mcpjunction.ai/servers/n8n-io--n8n
  install hint: npx n8n
  GitHub says: Fair-code workflow automation platform with native AI capabilities. Combine visual building with custom code, self-host or cloud, 400+ integrations.
-->


## punkpeye--awesome-mcp-servers

<!--
  punkpeye/awesome-mcp-servers  ·  language n/a  ·  92,330 stars  ·  MIT
  https://github.com/punkpeye/awesome-mcp-servers
  page: https://mcpjunction.ai/servers/punkpeye--awesome-mcp-servers
  install hint: none
  GitHub says: A collection of MCP servers.
-->
The most actively maintained community list of MCP servers, organised across 50-plus categories with high submission volume and frequent batched merges. Useful as a breadth-first starting point when you don't yet know what you're looking for, indexing everything from database connectors to niche APIs.

## github--github-mcp-server

<!--
  github/github-mcp-server  ·  Go  ·  32,256 stars  ·  MIT
  https://github.com/github/github-mcp-server
  page: https://mcpjunction.ai/servers/github--github-mcp-server
  install hint: go install github.com/github/github-mcp-server@latest
  GitHub says: GitHub's official MCP Server
-->
GitHub's own MCP server, which means it tracks API changes rather than lagging behind them the way community wrappers tend to. Covers code search, commit analysis, pull request management and Actions troubleshooting over one connection, and runs via npx, Docker, or direct Copilot integration. Worth scoping the personal access token deliberately — its permissions decide exactly how much of your account an agent can reach.

