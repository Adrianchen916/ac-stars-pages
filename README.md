# AC 的公开 GitHub Stars 项目库

这是 [Adrianchen916 的公开 Stars](https://github.com/Adrianchen916?tab=stars) 的可搜索网页。主页为 `index.html`，分类文档为 `stars.md`。

## 自动更新

仓库中的 [GitHub Actions 工作流](.github/workflows/update-stars.yml) 每月 1 日约北京时间 09:17 读取公开 GitHub API，运行 `python3 update_stars.py`，提交更新后的网页、Markdown 和 JSON 快照。也可以从 Actions 页面手动运行。GitHub 计划任务可能延迟；运行失败时脚本不会清空上次成功的数据。

新 Star 默认归入“待确认用途”，可在 `classifications.json` 中编辑主分类；随后手动运行工作流或等待下一次自动同步。此仓库只包含公开 Stars 及其衍生分类，不需要 GitHub Token 或 Cloudflare API Token。

## Cloudflare Pages 部署设置

在 Cloudflare Dashboard 中创建 Pages 项目，使用 Git 集成选择此仓库。生产分支选 `main`，框架预设选 `None`，构建命令填写：

```sh
mkdir -p public && cp index.html stars.md public/
```

构建输出目录填写 `public`，根目录留空，不需要环境变量。Cloudflare 会在仓库推送后重新部署。网页地址由 Cloudflare 在首次部署时分配，通常为 `项目名.pages.dev`。

如果你希望直接公开 JSON 数据，可把 `stars.json` 也加到构建命令的 `cp` 后面。当前网页已经内嵌数据，不依赖额外 JSON 请求。

## 本地使用

运行 `python3 update_stars.py` 后打开 `index.html`。脚本用系统 `curl` 或 Python 标准库读取公开 API；没有安装其他依赖。
