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

- 修复提交 823e36d 已推送 main；[工作流 43579661387](https://github.com/SmallXY/SmallXY/actions/runs/43579661387) 实际执行 success，测试、采集、生成校验、自动提交推送全部成功。
- 自动生成提交 33049a5 已拉取并再次 --check 通过，数据时间为 2026-11-14 09:15:32 UTC。
- 当前统计：个人非 Fork 仓库 11；参与外部仓库 61（原 64）；主要贡献组织项目 56（原 59）；作品 Star 33。被移除的参与记录净减少三个；登录对接仓库此前就不属于 SmallXY 的主要贡献项目。
- qianniu-cli-macos 已归档，离开热门榜但仍按原口径计入总 Star；PriceTemplete 仍公开未归档，保留在 GitHub 榜单，因此 Star 总数没有减少。当前前四为 purpur-config-cnnotes、PriceTemplete、AVMWandMod、CyanTemplete4TraeAI。
- README 中四个删除项目的旧 GitHub 链接与两个改名前的链接全部消失，改名后的 BukkitGenesis、CyanFabricTemplate 正常出现；六个 Gitee 项目入口完整保留。
- 六个 Gitee URL 使用禁用凭据助手的匿名 git ls-remote 验证，全部成功返回 HEAD。
- 线上 GitHub 1440px 与 390px 均 HTTP 200，8 张图片解码成功、响应式图片切换正确、两个折叠区可打开、页面无水平溢出、六个 Gitee 项目链接存在。已检查实际窄屏截图中的新榜单和迁移区。
- 本地直连 GitHub 网页一度超时；使用本机 Git 已配置的代理完成线上验收，没有改动系统代理或仓库工作流配置。

本次删仓、改名、归档和 Gitee 入口更新的全部关键验收通过。
