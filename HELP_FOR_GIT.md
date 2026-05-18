# Git 使用帮助（适用于 spacecraft-design-agent-demo 项目）

这份文档用于记录本项目的常用 Git 操作流程，尤其适合在使用 Codex / Roo Code 修改代码前后进行版本管理。

---

## 1. 基本原则

在让 AI 大改代码之前，先保存当前稳定版本。

在 AI 修改代码之后，确认项目能运行，再提交新版本。

推荐节奏：

```bash
git status
git add .
git commit -m "Save working version before next AI refactor"
git push
```

---

## 2. 查看当前状态

查看当前分支、是否有未提交修改：

```bash
git status
```

常见结果：

```text
nothing to commit, working tree clean
```

表示当前代码是干净的，没有未提交改动。

如果看到：

```text
Your branch is ahead of 'origin/main' by 1 commit
```

表示本地已经提交了新版本，但还没有推送到 GitHub，需要执行：

```bash
git push
```

---

## 3. 查看改了哪些文件

查看被修改的文件列表：

```bash
git diff --name-only
```

查看具体改动内容：

```bash
git diff
```

查看最近 5 次提交：

```bash
git log --oneline -5
```

---

## 4. 提交代码 Commit

### 4.1 添加所有改动

```bash
git add .
```

### 4.2 提交前再次检查

```bash
git status
```

确认没有 `.env`、API key、临时文件被加入。

如果不小心把 `.env` 加入了 staged changes，执行：

```bash
git restore --staged .env
```

并确认 `.gitignore` 中包含：

```gitignore
.env
*.env
.streamlit/secrets.toml
```

### 4.3 提交

```bash
git commit -m "你的提交说明"
```

示例：

```bash
git commit -m "Refactor Streamlit UI with clean panels and hidden debug logs"
```

---

## 5. 推送到 GitHub Push

正常推送：

```bash
git push
```

如果第一次推送或提示没有 upstream：

```bash
git push -u origin main
```

推送成功后检查：

```bash
git status
```

如果显示：

```text
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

说明本地和 GitHub 已同步。

---

## 6. 常用完整流程

每次修改完成后，建议按这个顺序执行：

```bash
git status
git diff --name-only
git add .
git status
git commit -m "说明这次改了什么"
git push
git status
git log --oneline -5
```

示例：

```bash
git status
git diff --name-only
git add .
git status
git commit -m "Improve orbit validation and inference workflow"
git push
git status
git log --oneline -5
```

---

## 7. 推荐 Commit Message

提交说明应该简洁描述“这次改了什么”。

推荐示例：

```bash
git commit -m "Initial working MVP with LLM extraction and orbit intelligence"
git commit -m "Add LLM-first parameter extraction with fallback"
git commit -m "Add orbit inference and consistency validation"
git commit -m "Add orbital element completeness gate"
git commit -m "Refactor Streamlit UI into research console layout"
git commit -m "Improve execution logs and debug panel"
git commit -m "Update project documentation and handoff rules"
```

---

## 8. AI 修改代码前的保护流程

在让 Codex / Roo Code 大改代码前，先保存当前版本。

如果当前有未提交修改：

```bash
git status
git add .
git commit -m "Save working version before AI refactor"
git push
```

如果当前没有改动，`git status` 会显示 clean，不需要提交。

---

## 9. AI 改坏了如何撤销

### 9.1 AI 改了代码，但还没有 commit

丢弃所有未提交修改：

```bash
git restore .
```

如果 AI 新建了一些文件，也想删除：

```bash
git clean -fd
```

更彻底的恢复方式：

```bash
git reset --hard
git clean -fd
```

注意：这些命令会删除未提交修改，执行前要确认真的不要这些改动。

### 9.2 已经 commit 了，但还没有 push

回退到上一个 commit：

```bash
git reset --hard HEAD~1
```

### 9.3 已经 push 了，但想安全撤销

推荐使用 revert，生成一个反向提交：

```bash
git revert HEAD
git push
```

不建议随便使用 force push。

---

## 10. 查看历史版本

查看提交历史：

```bash
git log --oneline
```

查看某个 commit 的详细改动：

```bash
git show <commit_id>
```

例如：

```bash
git show c44d25a
```

---

## 11. 查看远程仓库

查看当前远程仓库地址：

```bash
git remote -v
```

示例输出：

```text
origin  https://github.com/KH-123/spacecraft-design-agent-demo.git (fetch)
origin  https://github.com/KH-123/spacecraft-design-agent-demo.git (push)
```

如果需要重新设置远程地址：

```bash
git remote set-url origin https://github.com/KH-123/spacecraft-design-agent-demo.git
```

---

## 12. Push 网络失败怎么办

如果出现：

```text
Failed to connect to github.com port 443
Recv failure: Connection was reset
```

通常是网络无法连接 GitHub，不是代码或 commit 的问题。

先检查网络：

```powershell
Test-NetConnection github.com -Port 443
```

如果 `TcpTestSucceeded : False`，说明当前网络连不上 GitHub。

可以尝试：

- 换网络；
- 使用手机热点；
- 打开 VPN / 代理；
- 稍后重试。

如果使用 Clash，常见代理端口是 7890，可以配置 Git 走代理：

```bash
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

然后重新推送：

```bash
git push
```

如果代理配置错了，清除代理：

```bash
git config --global --unset http.proxy
git config --global --unset https.proxy
```

---

## 13. 检查 `.gitignore`

项目根目录建议包含 `.gitignore`，至少包括：

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
venv/
env/

# Environment variables and secrets
.env
*.env
.streamlit/secrets.toml

# IDE / OS
.vscode/
.idea/
.DS_Store
Thumbs.db

# Logs
*.log

# Generated outputs / local databases
outputs/
chroma_db/
data/chroma/
```

如果需要提供配置模板，可以提交 `.env.example`，但不要提交 `.env`。

`.env.example` 示例：

```env
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_TIMEOUT_SECONDS=30
```

---

## 14. 最常用命令速查

```bash
# 查看状态
git status

# 查看改动文件
git diff --name-only

# 查看具体改动
git diff

# 添加全部改动
git add .

# 提交
git commit -m "commit message"

# 推送
git push

# 查看最近提交
git log --oneline -5

# 查看远程仓库
git remote -v

# 撤销未提交修改
git restore .

# 删除未跟踪文件
git clean -fd

# 回退上一个未 push 的 commit
git reset --hard HEAD~1

# 安全撤销已经 push 的 commit
git revert HEAD
```

---

## 15. 推荐工作习惯

1. 每次 AI 大改前，先 commit 当前稳定版本。
2. 每次 AI 大改后，确认能运行，再 commit。
3. `.env` 和 API key 永远不要提交。
4. commit message 写清楚“这次改了什么”。
5. push 失败通常是网络问题，本地 commit 不会丢。
6. 重大改动前先运行：

```bash
git status
git log --oneline -5
```

7. 修改后至少运行：

```bash
python -m py_compile app.py agents/*.py
streamlit run app.py
```

确认没问题后再 commit。
