# 个人主页维护说明

## 目标与边界

- 呈现「六欲玄易 / SmallXY」个人形象、本人提供的照片、公开作品和贡献足迹。
- 根目录 README.md 是 GitHub Profile 的必要文件，已获准作为文档路径规则的唯一例外；其他说明与数据均位于 docs/。
- 只修改本仓库的 README、assets、scripts、tests、.github、docs 和必要的 Git 配置文件；不修改账号头像、简介、置顶仓库或其他项目。
- 不制造贡献、Star、维护者或创始人身份，不将 Fork 视为原创，不把组织所有项目算作个人作品。
- 新增文本文件使用 UTF-8 无 BOM、LF。原 githubbanner.png 保留，不再引用。

## 验收标准

1. 桌面与 390px 窄屏显示完整、无页面水平溢出；深浅主题均能辨识封面、照片、统计和项目卡。
2. README 中图片全部来自仓库，无第三方统计图片服务；照片不带 EXIF 元数据。
3. 数字与 docs/profile-data.json 一致，榜单可复现，创建日期与推送日期分开。
4. 组织项目仅在 Contributors 中 SmallXY 的提交数为最高（含并列）时纳入作品榜；保留组织归属。
5. 分页、空数据、并列、归档/Fork 过滤、内容转义、更新失败保护、重复生成均有自动化测试。
6. GitHub Actions 实际运行成功，推送后检查 GitHub 个人主页中的图片、数据和折叠区。

## 统计口径

所有统计仅面向公开数据，不读取或发布私有仓库信息。身份匹配忽略账号大小写。

| 指标 | 定义 |
| --- | --- |
| 个人非 Fork 仓库 | SmallXY 名下全部公开非 Fork 仓库，包含归档仓库与本介绍仓库。不是贡献项目数。 |
| 参与外部仓库 | 非本人名下仓库中，公开 Commit 搜索、公开 PR 搜索与公开组织 Contributors 能核对到参与记录的仓库去重数。Commit 搜索排除 Fork 镜像；PR 不要求已合并。 |
| 主要贡献组织项目 | 账号公开组织的非 Fork 仓库，Contributors 中 SmallXY 提交数大于零且等于最高账号关联提交数（含并列），包含归档仓库与组织介绍仓库。 |
| 作品获星 | 个人非 Fork 仓库 + 上述主要贡献组织项目的 Star 总和，排除 SmallXY 和 .github 介绍仓库，包含归档。各仓库的 Star 相加，不是去重后的用户数。 |
| 热门作品 | 作品范围内非归档仓库的 Star 前四；同星按最近推送降序，再按完整仓库名升序。不代表近期增长速度。 |
| 最近项目 | 同一非归档作品范围，按 created_at 降序选前三。 |

GitHub Contributors 按提交量排序，可能缓存数小时；账号关联只覆盖前 500 个作者邮箱。该排名不衡量代码质量，也不代表唯一作者、创始人或正式维护者身份。

Commit 搜索只覆盖 GitHub 已索引的默认分支，不能代替 GitHub 全量贡献图。非公开组织成员关系不会被发现；公开组织范围由 /users/SmallXY/orgs 自动获取。项目创建日期是仓库 created_at，不是首次创意、最早提交或产品发布日。日期统一显示 UTC。

所有列表分页读取。GitHub 搜索结果若不完整、超过每次查询 1,000 条上限、分页途中数量变化或 API 请求失败，更新会失败并保留上一版已发布数据，不用零值替换。未来超过搜索上限时需要改为按时间分段查询后才能恢复更新。

## 更新方式

GitHub Actions：每天 UTC 00:23（北京时间 08:23）尝试刷新；也支持 Actions → Refresh profile → Run workflow，以及修改相关代码后的 push 触发。调度由 GitHub 执行，可能延迟；公开仓库 60 天没有活动时定时工作流可能被停用。无需外部统计服务或自建服务器。

工作流使用 GitHub 自动提供的 GITHUB_TOKEN，只需要 contents: write 提交生成文件，不需要个人访问令牌。若仓库写权限或分支保护拒绝机器人直接推送，需要调整对应仓库策略。

本地（Python 3.10+，仅标准库）：

    python -m unittest discover -s tests -v
    python scripts/update_profile.py
    python scripts/update_profile.py --check

重新渲染已保存快照、不访问 API：

    python scripts/update_profile.py --offline

首次本地采集可选用 --cache-dir docs/.cache/<本次采集名>，避免网络失败后重复请求；这是一次采集的断点缓存，不是长期缓存。每次新采集必须换新目录，工作流不使用此缓存。不要把缓存或任何令牌提交到仓库。

个人文案和照片在 README 自动生成标记之外维护；热门榜、最近项目、统计卡、贡献证据由 scripts/update_profile.py 生成。照片为用户指定图片的缩小、圆角加框版本，没有改变人物内容；原文件不修改。

## 官方参考

- [Profile README 要求](https://docs.github.com/en/account-and-profile/how-tos/profile-customization/managing-your-profile-readme)
- [仓库与 Contributors API](https://docs.github.com/en/rest/repos/repos#list-repository-contributors)
- [Search API 与限制](https://docs.github.com/en/rest/search/search)
- [工作流调度](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [折叠区语法](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-collapsed-sections)
