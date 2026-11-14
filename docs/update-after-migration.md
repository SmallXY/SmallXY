# 删仓与迁移后的主页更新

日期：2026-11-14。

## 目标与验收

- 仅修改本个人主页仓库，保留封面、照片和布局，不修改源项目、Gitee 项目或账号资料。
- GitHub 数字和热门榜按当前公开仓库重新采集；删除、归档、改名分别处理，不沿用已删除项目的历史 Star。
- 六个迁移项目保留 Gitee 入口，但不将 Gitee 数量或 Star 混入 GitHub 统计。
- 修复搜索索引延迟造成的旧名、已删除仓库重复计数或失效证据。
- 自动化测试、数据一致性、窄屏/桌面预览、实际 GitHub Actions 刷新和线上页面均需通过。

## 已核对的来源

- 已读取关联任务「迁移 CyanBukkit 项目至 Gitee」，获知六个目标路径与代码迁移报告；本次未向该任务发送消息。
- Gitee MCP 再次读取公开仓库列表，确认六个目标均 public=1，路径为 cyanbukkit 下的 CyanShop_Backend、CyanShop_Frontend、CyanBukkitOfficial、PriceTemplete、qianniu-cli-macos、Cyanbukkit_api_microsoft。
- GitHub 最新组织列表出现 BukkitGenesis、CyanFabricTemplate；旧名 AIBukkitProject 的仓库 API 重定向到 BukkitGenesis。
- 四个旧项目不再出现在 CyanBukkit 公开仓库列表：CyanShop_Backend、CyanShop_Frontend、CyanBukkitOfficial、Cyanbukkit_api_microsoft。
- qianniu-cli-macos 仍公开但 archived=true；PriceTemplete 仍公开且未归档。因此不能把六个迁移项目一律视为 GitHub 已删除。
- 已查阅 GitHub 官方 [重定向与 API 最佳实践](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api#follow-redirects)。

## 发布前验证

- 13 项 unittest 通过，新增删除/改名/转私有/转个人名下、规范名去重、404/410 与 403 区分、查证失败不静默删除证据的测试。
- 本地 1200px、390px × 深浅主题预览通过：8 张图片成功加载，页面无水平溢出，两个折叠区可打开，新增 Gitee 区域保留。
- 文本编码与图片/快照检查通过，git diff --check 通过。
- 本机匿名 API 配额耗尽（HTTP 403，remaining=0），初次刷新按设计失败并保留旧快照和旧时间戳；没有宣称旧数据为新数据。后续通过仓库现有 GitHub Actions 的 GITHUB_TOKEN 完成认证刷新，不增加个人令牌或依赖。

## 发布后验证

待推送修复并完成认证刷新后记录实际结果；本段尚不代表新统计已发布。
