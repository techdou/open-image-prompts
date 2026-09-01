<p align="center">
  <img src="./assets/readme/hero-zh.svg" width="100%" alt="Open Image Prompts">
</p>

<p align="center">
  <a href="./README.md">English</a> · <strong>简体中文</strong>
</p>

<p align="center">
  🌐 在线演示：<a href="https://oi.techdou.cn"><strong>oi.techdou.cn</strong></a>
</p>

# Open Image Prompts

一个开源、本地优先的视觉提示词资料库，并提供两个可以安装到智能体中的 Skill：

- `img-gen-taste`：把模糊需求整理成明确的美术方向。
- `img-gen-prompts`：检索可追溯的提示词—图片参考，并打开本地对比画廊。

> **关于本仓库** — 这是 [techdou](https://github.com/techdou) 的个人二创分支，基于上游项目 [NanmiCoder/open-image-prompts](https://github.com/NanmiCoder/open-image-prompts)。除同步上游数据发布外，还包含一批界面与交互优化：默认浅色主题 + 一键切换深色、favicon/页头/页脚统一的几何 Logo、重排的手机端筛选布局、触屏设备卡片信息常显等。详见[本分支的改动](#本分支的改动)。

用编程智能体接入？[AGENTS.md](./AGENTS.md) 是精简版的安装、端口与 Skill 约定说明。

公开数据集包含 **17,327 条来源提示词**、**30,722 张图片**、**34,648 条翻译**、**201,808 条有效 v2 提示词标签**和 **185 个封闭视觉标签**。打标模型、回填工具、供应商配置、测试批次、错误日志以及其他打标过程记录均不在公开仓库中。以上数字由 `npm run verify:docs` 与 `data/public-corpus.json` 对账。

数据资产通过 [GitHub Releases](https://github.com/NanmiCoder/open-image-prompts/releases) 分发（不再使用 Git LFS）：仓库克隆保持轻量，`scripts/fetch_dataset.py` 会下载 SQLite 归档（约 80 MB）以及可选的按月图片包（合计约 4.3 GB），并做 sha256 校验。完整资产清单见 `data/dataset-manifest.json`。

## 本分支的改动

- **主题系统** — 默认浅色「Day Gallery」主题，页头按钮一键切换回原始深色「Night Gallery」；选择保存在 `localStorage`，首帧渲染前生效（不闪屏），并同步手机浏览器地址栏颜色。
- **主题语义分离** — 叠在图片上的元素（卡片渐变、徽章、详情弹窗媒体区）在两种主题下都保持深色灯箱；提示词文本框等凹陷容器跟随主题变化。
- **统一 Logo** — 几何「OI」标识（黄铜圆角方块）贯穿 favicon、页头、页脚。
- **手机端布局** — 搜索、排序、筛选行重新分组并留出呼吸空间；排序切换器不再与筛选标签挤在一起；触屏设备上卡片摘要、作者与复制按钮常显。
- **细节打磨** — 深色主题的全局滚动条、画廊浏览时筛选栏自动紧凑收起（按 `/` 可随时唤出搜索框）。

## 代码仓库和数据集的关系

这个仓库本身只跟踪代码、前端、API、Skills、taxonomy 和轻量索引文件，不直接把数据库和图片提交进 Git 历史。实际数据通过 GitHub Releases 下载到本地 checkout：

```text
open-image-prompts/
├── db/prompts.db.gz        # SQLite 数据集归档，来自 Release，gitignored
├── images/                 # 图片包解压目录，来自 Release，gitignored
├── .oip/runtime/prompts.db # 运行时解压后的只读 SQLite，gitignored
├── data/dataset-manifest.json
├── data/public-corpus.json
└── web/dims.json
```

如果只 clone 仓库而不下载数据，前端/API/Skill 只有代码，不能完整本地预览和检索。首次使用请在仓库根目录执行：

```bash
npm run data:pull          # 下载 DB + 全量图片包，并校验 sha256
```

只想先下载 DB、不下载几 GB 图片包，可以执行：

```bash
npm run data:pull:db
# 或者
python3 scripts/fetch_dataset.py --db-only
```

此时检索可以工作，画廊会尽量回退到原始来源图片地址；完整本地图片预览需要下载图片包。

后续数据集更新时，Git commit 通常只更新 `data/dataset-manifest.json`、`data/public-corpus.json`、`web/dims.json` 这些小文件；`prompts.db.gz` 和 `images-YYYY-MM.tar.gz` 作为 Release assets 发布。用户重新运行 `npm run data:pull` 即可根据 manifest 下载新版 DB，并且只拉取 sha256 变化的图片包。

## 一键启动

先安装 [Git](https://git-scm.com/downloads) 和 [Node.js](https://nodejs.org/) 20.19+ 或 22.12+，然后克隆仓库：

```bash
git clone https://github.com/techdou/open-image-prompts.git
cd open-image-prompts
```

macOS 或 Linux：

```bash
./start.sh
```

Windows：

```bat
start.bat
```

也可以直接在文件管理器中双击 `start.bat`。启动脚本会按需安装 [uv](https://docs.astral.sh/uv/)、创建兼容的 Python 环境、从 GitHub Releases 下载数据集、安装前端依赖，并同时启动前后端。打开终端输出的本地地址即可。如果想跳过体积较大的图片包（画廊会回退到原始来源图片地址），启动前设置 `OIP_FETCH_SKIP_IMAGES=1`。

首次启动会把压缩 SQLite 解压到已忽略的 `.oip/runtime/`；后续启动会复用 Python 环境，并按锁文件刷新依赖。

日常改前端时，可以用 `node web/scripts/with_api.mjs dev` 同时启动 API 和 Vite 开发服务器。

## 数据集资产

Git 仓库不会直接保存大体积数据文件。克隆仓库后，你拿到的是应用代码、Skills、公开元数据和 `data/dataset-manifest.json`。要完整运行本地画廊，还需要从 GitHub Releases 下载 SQLite 数据库和图片包。

下载完整数据集：

```bash
npm run data:pull
```

这个命令会读取 `data/dataset-manifest.json`，下载 Release 资产，校验 sha256，并把文件放到应用期望的位置：

- `db/prompts.db.gz`：压缩后的公开 SQLite 数据库。
- `images/`：从 `images-YYYY-MM.tar.gz` 解压出来的按月图片包。
- `.oip/packs/`：本地解压标记，下次执行时会跳过未变化的图片包。

如果只想下载数据库，让画廊回退到原始来源图片地址：

```bash
npm run data:pull:db
```

这些生成文件会被 Git 忽略。数据集可以频繁发布，但仓库 commit 仍然保持轻量：Git 只跟踪代码和小体积元数据，`prompts.db.gz` 和图片归档通过 GitHub Releases 分发。

## 使用 Docker

Docker 会提供包含 Node.js 22 与 Python 3 的 Linux 隔离环境。镜像构建阶段会先执行公开数据校验、API/前端测试、lint 和生产构建，全部通过后才生成运行镜像：

```bash
docker build -t open-image-prompts .
docker run --rm --name open-image-prompts -p 4173:4173 open-image-prompts
```

然后访问 <http://localhost:4173>。API 仍然只监听容器内部回环地址，仅通过前端代理对外提供；容器使用非特权 `node` 用户运行，并提供 `/health` 健康检查。

构建过程会从 GitHub Releases 下载 SQLite 归档（需要能访问 github.com），图片通过原始来源地址回退展示。以上命令适用于 Windows/macOS 的 Docker Desktop 和 Linux Docker Engine。

### 对外部署（反向代理 / 域名访问）

生产部署有三个实用要点：

1. **域名白名单**：容器内的预览服务器默认只接受 `localhost` 的 Host 头。通过域名或反向代理（Cloudflare Tunnel、Nginx 等）对外服务时，在 `web/vite.config.js` 的 `preview` 配置中加上域名，否则公网访问会返回 403：

   ```js
   preview: {
     allowedHosts: ['your.domain.example'],
     // ...
   }
   ```

2. **数据走 volume，不打进镜像**：完整图片包解包后约 4.8 GB，打进镜像会让每次重建都拖着数 GB 的构建上下文。推荐把 `images/` 与 `db/` 挂载进容器，镜像更新与数据更新互不影响：

   ```bash
   docker run -d --name open-image-prompts-prod --restart unless-stopped \
     -p 127.0.0.1:4173:4173 \
     -v "$PWD/images:/app/images:ro" \
     -v "$PWD/db:/app/db" \
     open-image-prompts
   ```

3. **离线安装数据集**：构建环境到 GitHub 网络不稳时，可先在宿主机把资产下载好（自行校验 sha256），再用脚本原生的离线模式安装，全程不联网：

   ```bash
   python3 scripts/fetch_dataset.py --assets-dir /path/to/prepared-assets
   ```

   数据集发布新版本后，重新执行上述命令（按 `.oip/packs` 标记增量解包）并重启容器即可生效。

## 安装 Skills

查看并安装两个 Skill：

```bash
npx skills add techdou/open-image-prompts --list
npx skills add techdou/open-image-prompts -g
```

`img-gen-taste` 使用内置风格卡，可以直接工作。`img-gen-prompts` 使用本仓库的公开 SQLite 和已审核图片：

```bash
export OIP_REPO_ROOT="$PWD"  # PowerShell: $env:OIP_REPO_ROOT = (Get-Location)
npm run status
```

准备完成后会返回 `"active_taxonomy_version": "oip-visual-v2"` 和 `"ready": true`。

搜索结果中的 `results` 始终是严格匹配。如果严格结果不足，独立的
`related_results` 会补充"仅缺少一个已声明审美偏好"的图片侧确认参考，
不会把它冒充严格命中。这项能力不增加向量数据库、模型下载、API Key 或
Python 依赖。可以运行包含相关图片人工视觉判定的 72 条中英双语标注回归基准：

```bash
npm run test:retrieval
```

## 公开数据边界

公开 DB 只保留产品运行所需数据：

- 来源提示词与来源链接；
- 已审核通过的本地图片记录；
- 中英文翻译；
- 有效 `oip-visual-v2` 提示词/图片标签；
- 公开 taxonomy 与 FTS 搜索索引。

公开 DB 不包含候选标签、模型或供应商配置、run ID、租约、模型理由、错误路径、评估表和 legacy 标签。

更多信息见 [DATASET.md](./DATASET.md)、[DATA_LICENSE.md](./DATA_LICENSE.md) 和机器可读的 [公开语料清单](./data/public-corpus.json)。

## 目录结构

```text
open-image-prompts/
├── server/       # 本地 API（只读 SQLite）
├── web/          # React + Vite 前端（画廊、筛选、提示词详情）
├── skills/       # 可安装的 Agent Skills（img-gen-prompts、img-gen-taste）
├── retrieval/    # 检索引擎与意图配置
├── scripts/      # 数据集下载、校验与工具脚本
├── data/         # 随仓库提交的轻量数据索引与清单
├── taxonomy/     # 视觉标签体系（oip-visual-v2）
├── evals/        # 检索基准测试
├── runtime/      # 运行时辅助（归档数据库、提示词库）
└── tests/        # API 与画廊测试
```

## 验证

```bash
uv sync --locked
npm --prefix web ci
npm test
npm run lint
npm run build
npm run status
```

API 与 Skill 均以只读 immutable 模式打开 SQLite。所有服务默认只绑定 `127.0.0.1`，不会启动任何打标任务。前端从 `5173` 开始，端口被占用时自动顺延到下一个空闲端口，并打印它实际监听的地址；用 `OIP_WEB_HOST`/`OIP_WEB_PORT` 可以固定，此时端口冲突会直接报错而不是悄悄换端口。Skill 的画廊桥接服务在 `4173` 上是同样的行为。

## 许可证

应用代码与 Skill 指令使用 [MIT License](./LICENSE)。数据许可和第三方内容边界单独记录在 [DATA_LICENSE.md](./DATA_LICENSE.md)。

本分支沿用上游的 MIT 代码许可。感谢 [NanmiCoder](https://github.com/NanmiCoder) 与所有上游贡献者的原始项目和持续的数据集发布。
