"""Refresh public GitHub evidence and render a dependency-free profile."""

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
USER = 'SmallXY'
API = 'https://api.github.com'
START, END = '<!-- PROFILE:START -->', '<!-- PROFILE:END -->'
FONT = 'Segoe UI, PingFang SC, Microsoft YaHei, Noto Sans CJK SC, sans-serif'
COLORS = {'Java': '#e9b579', 'Kotlin': '#b79aff', 'Python': '#86baf1',
          'TypeScript': '#7bb5ed', 'JavaScript': '#e9d27e', 'Vue': '#80d8b5',
          'Go': '#7cd7e5', 'C#': '#bda0e8', 'HTML': '#efac96'}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


class GitHub:
    def __init__(self, cache=None):
        self.cache = Path(cache) if cache else None
        self.token = os.environ.get('GITHUB_TOKEN')

    def get(self, path, *, missing_ok=False, **params):
        url = API + path + ('?' + urlencode(params) if params else '')
        cached = self.cache / (hashlib.sha256(url.encode()).hexdigest() + '.json') if self.cache else None
        if cached and cached.exists():
            data = json.loads(cached.read_text(encoding='utf-8'))
            if data is None and not missing_ok:
                raise RuntimeError(f'GitHub repository unavailable: {path}')
            return data
        headers = {'User-Agent': 'SmallXY-profile', 'Accept': 'application/vnd.github+json',
                   'X-GitHub-Api-Version': '2022-11-28'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers=headers), timeout=45) as response:
                    data = [] if response.status == 204 else json.load(response)
                if cached:
                    write(cached, json.dumps(data, ensure_ascii=False) + '\n')
                return data
            except HTTPError as exc:
                if exc.code in (404, 410) and missing_ok:
                    if cached:
                        write(cached, 'null\n')
                    return None
                if exc.code in (403, 429) and attempt < 2:
                    retry = exc.headers.get('Retry-After')
                    reset = exc.headers.get('X-RateLimit-Reset')
                    delay = int(retry) if retry and retry.isdigit() else (max(1, int(reset) - int(time.time()) + 1) if reset else 15)
                    if delay <= 90:
                        time.sleep(delay)
                        continue
                elif exc.code >= 500 and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f'GitHub HTTP {exc.code}: {path}; published data left unchanged.') from exc
            except (URLError, TimeoutError) as exc:
                if attempt == 2:
                    raise RuntimeError(f'GitHub unavailable: {path}; published data left unchanged.') from exc
                time.sleep(2 ** attempt)

    def pages(self, path, **params):
        result = []
        for page in range(1, 1001):
            rows = self.get(path, per_page=100, page=page, **params)
            if not isinstance(rows, list):
                raise ValueError(f'Expected a list from {path}')
            result.extend(rows)
            if len(rows) < 100:
                return result
        raise ValueError('Pagination exceeded safety limit')

    def search(self, kind, query):
        # Never publish truncated search counts (GitHub's limit is 1,000).
        result = []
        total = None
        for page in range(1, 11):
            data = self.get('/search/' + kind, q=query, per_page=100, page=page,
                            sort='author-date' if kind == 'commits' else 'created', order='asc')
            if data['incomplete_results'] or data['total_count'] > 1000:
                raise ValueError('GitHub search incomplete or above 1,000 results; refusing to replace published counts.')
            if total is not None and total != data['total_count']:
                raise ValueError('Search changed during pagination; retry with a fresh cache.')
            total = data['total_count']
            result.extend(data['items'])
            if len(result) >= total:
                if len(result) != total:
                    raise ValueError('Search result count mismatch')
                return result
        raise ValueError('Search pagination incomplete')


def compact(repo, scope):
    return {key: repo[key] for key in ('full_name', 'html_url', 'description', 'stargazers_count',
            'fork', 'archived', 'created_at', 'pushed_at', 'language')} | {'scope': scope}


def contribution(contributors):
    highest = max((c['contributions'] for c in contributors), default=0)
    mine = next((c['contributions'] for c in contributors if c.get('login', '').lower() == USER.lower()), 0)
    leaders = [c.get('login', '(anonymous)') for c in contributors if c['contributions'] == highest]
    return {'commits': mine, 'top_commits': highest, 'is_lead': mine > 0 and mine == highest,
            'tied': mine > 0 and mine == highest and len(leaders) > 1, 'leaders': leaders}


def contribution_evidence(api, commits, prs, org_repos):
    # Search indexing can lag behind deletion, renaming or visibility changes.
    # Known organization repositories come from this refresh's public inventory;
    # other search results must resolve to a current public repository first.
    resolved = {r['full_name'].lower(): r for r in org_repos}

    def current(name):
        key = name.lower()
        if key not in resolved:
            resolved[key] = api.get('/repos/' + name, missing_ok=True)
        repo = resolved[key]
        if not repo or repo.get('private') or repo['full_name'].split('/')[0].lower() == USER.lower():
            return None
        return repo

    evidence = {}
    for kind, items in [('commit', commits), ('pr', prs)]:
        for item in items:
            name = item['repository']['full_name'] if kind == 'commit' else item['repository_url'].removeprefix(API + '/repos/')
            repo = current(name)
            if not repo or (kind == 'commit' and repo.get('fork')):
                continue
            canonical = repo['full_name']
            suffix = '/commit/' + item['sha'] if kind == 'commit' else '/pull/' + str(item['number'])
            evidence.setdefault(canonical, {'commit': None, 'pr': None, 'contributors': None})[kind] = repo['html_url'] + suffix
    for repo in org_repos:
        if repo['contribution']['commits']:
            name = repo['full_name']
            evidence.setdefault(name, {'commit': None, 'pr': None, 'contributors': None})['contributors'] = API + '/repos/' + name + '/contributors'
    return dict(sorted(evidence.items()))


def collect(api):
    user = api.get('/users/' + USER)
    own = [compact(r, 'personal') for r in api.pages('/users/' + USER + '/repos', type='owner') if not r.get('private')]
    orgs = sorted(o['login'] for o in api.pages('/users/' + USER + '/orgs'))
    org_repos = []
    for org in orgs:
        for raw in api.pages('/orgs/' + org + '/repos', type='public'):
            if raw['fork'] or raw.get('private'):
                continue
            repo = compact(raw, 'organization')
            print('Checking contributors:', repo['full_name'], flush=True)
            repo['contribution'] = contribution(api.pages('/repos/' + repo['full_name'] + '/contributors'))
            org_repos.append(repo)
    commits = api.search('commits', f'author:{USER} -user:{USER}')
    prs = api.search('issues', f'author:{USER} is:pr is:public -user:{USER}')
    evidence = contribution_evidence(api, commits, prs, org_repos)
    return {'schema_version': 1, 'updated_at': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
            'account_created_at': user['created_at'], 'public_organizations': orgs,
            'personal_repositories': own, 'organization_repositories': org_repos,
            'external_contribution_evidence': evidence,
            'search_totals': {'external_indexed_commits': len(commits), 'external_public_prs': len(prs)}}


def selections(data):
    personal = [r for r in data['personal_repositories'] if not r['fork']]
    lead = [r for r in data['organization_repositories'] if r['contribution']['is_lead']]
    pool = [r for r in personal + lead if r['full_name'].split('/')[1].lower() not in (USER.lower(), '.github')]
    active = [r for r in pool if not r['archived']]
    # Stable ties: recent push, then full repository name.
    by_push = sorted(sorted(active, key=lambda r: r['full_name'].lower()), key=lambda r: r['pushed_at'] or '', reverse=True)
    popular = sorted(by_push, key=lambda r: r['stargazers_count'], reverse=True)[:4]
    latest = sorted(active, key=lambda r: (r['created_at'], r['full_name']), reverse=True)[:3]
    stats = [('个人非 Fork 仓库', len(personal)), ('参与外部仓库', len(data['external_contribution_evidence'])),
             ('主要贡献组织项目', len(lead)), ('作品获星', sum(r['stargazers_count'] for r in pool))]
    return popular, latest, stats


def esc(value):
    return html.escape(str(value), quote=True)


def clean(value):
    return ' '.join(str(value or '').split())


def wrap(value, width, count):
    lines, line, units = [], '', 0
    for char in clean(value):
        size = 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
        if units + size > width:
            lines.append(line.rstrip())
            line, units = '', 0
        line += char
        units += size
    if line:
        lines.append(line.rstrip())
    if len(lines) > count:
        lines = lines[:count]
        lines[-1] = lines[-1][:-1] + '…'
    return lines


def svg(width, height, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">\n'
            f'<title id="title">{esc(title)}</title>\n'
            f'<g font-family="{FONT}">{body}</g>\n</svg>\n')


def text(x, y, value, size=14, fill='#dce9ec', extra=''):
    return f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" {extra}>{esc(value)}</text>'


def render_stats(stats, date, mobile=False):
    width, height = (440, 258) if mobile else (1000, 154)
    body = f'<rect width="{width}" height="{height}" rx="16" fill="#101b23"/>'
    body += text(26, 30, 'OPEN SOURCE / 公开足迹', 12, '#8da5b4', 'letter-spacing="1.5"')
    for i, (label, value) in enumerate(stats):
        x = 26 + (i % 2) * 218 if mobile else 28 + i * 248
        y = 85 + (i // 2) * 96 if mobile else 91
        body += text(x, y, str(value).zfill(2), 42, '#b4f0df' if i % 2 == 0 else '#d5c8ff', 'font-weight="600"')
        body += text(x, y + 27, label, 14, '#acbec8')
    body += text(26, height - 15, 'PUBLIC DATA · ' + date, 10, '#829ba9', 'letter-spacing="1"')
    return svg(width, height, '公开足迹：' + '；'.join(f'{label} {value}' for label, value in stats), body)


def render_repo(repo, index):
    org = repo['scope'] == 'organization'
    color = '#b4a0e6' if org else '#7adbc7'
    owner, name = repo['full_name'].split('/')
    role = '组织 / 主要贡献者' + (' · 并列' if repo.get('contribution', {}).get('tied') else '') if org else '个人项目'
    body = '<rect x="1" y="1" width="478" height="278" rx="18" fill="#101b23" stroke="#2a3c49"/>'
    body += f'<path d="M25 27h24" stroke="{color}" stroke-width="3"/>'
    body += text(60, 32, owner.upper(), 11, '#91a9b7', 'letter-spacing="1.4"')
    body += text(451, 34, f'{index:02}', 17, color, 'text-anchor="end"')
    for i, line in enumerate(wrap(name, 33, 2)):
        body += text(25, 72 + 25 * i, line, 21, '#edf4f5', 'font-weight="600"')
    for i, line in enumerate(wrap(repo['description'] or '代码与想法，留在这里。', 48, 2)):
        body += text(25, 133 + i * 21, line, 14, '#a8bdc8')
    body += text(25, 188, role, 12, color)
    body += '<path d="M25 204h430" stroke="#293b47"/>'
    language = repo['language'] or '未标注语言'
    body += f'<circle cx="30" cy="224" r="4" fill="{COLORS.get(language, "#93a6b0")}"/>'
    body += text(42, 229, language, 12, '#bbccd4')
    body += text(455, 229, str(repo['stargazers_count']) + ' STARS', 12, '#e9d2a0', 'text-anchor="end"')
    body += text(25, 259, '创建 ' + repo['created_at'][:10], 11, '#94aab7')
    body += text(455, 259, '推送 ' + (repo['pushed_at'] or '—')[:10], 11, '#94aab7', 'text-anchor="end"')
    return svg(480, 292, repo['full_name'] + ' · ' + role + ' · ' + str(repo['stargazers_count']) + ' stars', body)


def md(value):
    return esc(clean(value)).replace('|', '&#124;').replace('[', '&#91;').replace(']', '&#93;').replace(chr(96), '&#96;').replace('*', '&#42;').replace('_', '&#95;')


def generated(data):
    popular, latest, stats = selections(data)
    stamp = data['updated_at'].replace('T', ' ').replace('Z', ' UTC')
    lines = [START, '<!-- Generated from public GitHub API data. Do not edit this section by hand. -->',
             '<picture>', '  <source media="(max-width: 600px)" srcset="assets/generated/stats-mobile.svg">',
             '  <img src="assets/generated/stats.svg" width="100%" alt="' + '；'.join(f'{label}：{value}' for label, value in stats) + '">', '</picture>', '',
             f'<sub>数据更新于 {stamp} · 仅公开数据 · [统计口径](docs/profile.md#统计口径)</sub>', '',
             '## 01 / 被星光选中的作品', '',
             '个人项目，以及我在组织中提交数第一（含并列）的项目。按 Star 排序，排除 Fork、归档和介绍仓库。', '']
    lines += ['<p align="center">']
    for i, repo in enumerate(popular):
        lines += [f'<a href="{esc(repo["html_url"])}"><img src="assets/generated/project-{i+1}.svg" width="420" alt="{esc(repo["full_name"])} · {repo["stargazers_count"]} stars"></a>']
    lines += ['</p>']
    if not popular:
        lines += ['暂时没有符合范围的公开项目。']
    lines += ['', '## 02 / 最近种下的想法', '', '同一作品范围，按仓库创建日期排序。不是发布日，也不等同于项目实际启动日。', '']
    for repo in latest:
        role = '组织 · 主要贡献者' if repo['scope'] == 'organization' else '个人'
        owner, name = repo['full_name'].split('/')
        lines += [f'**{repo["created_at"][:10]}** · [{md(name)}]({repo["html_url"]})<br>',
                  f'<sub>{owner} / {role} · 最近推送 {(repo["pushed_at"] or "—")[:10]} UTC</sub>', '']
    lines += ['', '## 03 / 一起写过的世界', '',
              '组织不是一个人的作品。这里记录我参与的部分，也保留它们原本的归属。', '',
              '<details>', '<summary>展开组织主要贡献项目、提交数与 Star</summary>', '',
              '“主要贡献”仅指 GitHub Contributors 中账号关联提交数第一；不代表创始人、唯一作者或维护者身份。提交统计可能有数小时缓存。', '',
              '| 组织项目 | 我的提交 / 最高提交 | Star | 仓库创建（UTC） |', '| :--- | ---: | ---: | :--- |']
    leads = sorted([r for r in data['organization_repositories'] if r['contribution']['is_lead']],
                   key=lambda r: (-r['contribution']['commits'], r['full_name']))
    for repo in leads:
        c = repo['contribution']
        status = ' · 已归档' if repo['archived'] else ''
        if c['tied']:
            status += ' · 并列'
        lines += [f'| [{md(repo["full_name"])}]({repo["html_url"]}){status} | {c["commits"]} / {c["top_commits"]} | {repo["stargazers_count"]} | {repo["created_at"][:10]} |']
    lines += ['', '</details>', '', '<details>', '<summary>展开外部仓库参与证据</summary>', '',
              '按公开默认分支 Commit、公开 PR 与公开组织 Contributors 去重；不含个人名下仓库，也不是 GitHub 全量贡献图。PR 记录不等于已合并。', '']
    for name, evidence in data['external_contribution_evidence'].items():
        links = ' / '.join(f'[{label}]({evidence[key]})' for key, label in [('commit', 'Commit'), ('pr', 'PR'), ('contributors', 'Contributors')] if evidence[key])
        lines += [f'- [{md(name)}](https://github.com/{name}) — {links}']
    lines += ['', '</details>', '',
              f'<sub>GitHub 起点：{data["account_created_at"][:10]} · 公开组织：' + ' / '.join(data['public_organizations']) + ' · [数据快照](docs/profile-data.json) · [更新方式](docs/profile.md)</sub>', END]
    assets = {'stats.svg': render_stats(stats, data['updated_at'][:10]), 'stats-mobile.svg': render_stats(stats, data['updated_at'][:10], True)}
    assets.update({f'project-{i+1}.svg': render_repo(r, i+1) for i, r in enumerate(popular)})
    return '\n'.join(lines), assets


def replace_block(readme, block):
    if readme.count(START) != 1 or readme.count(END) != 1 or readme.index(END) < readme.index(START):
        raise ValueError('README requires exactly one ordered marker pair')
    return readme[:readme.index(START)] + block + readme[readme.index(END) + len(END):]


def check(root=ROOT):
    data = json.loads((root / 'docs/profile-data.json').read_text(encoding='utf-8'))
    readme = (root / 'README.md').read_text(encoding='utf-8')
    block, assets = generated(data)
    if replace_block(readme, block) != readme:
        raise ValueError('README differs from the committed snapshot')
    for name, content in assets.items():
        if (root / 'assets/generated' / name).read_text(encoding='utf-8') != content:
            raise ValueError(f'Generated asset mismatch: {name}')
    for link in re.findall(r'(?:src|srcset)="([^"]+)"', readme):
        if link.startswith(('https:', 'http:', 'data:')) or not (root / link).is_file():
            raise ValueError(f'Image must be an existing repository file: {link}')
    for path in (root / 'assets').rglob('*.svg'):
        tree = ET.fromstring(path.read_text(encoding='utf-8'))
        for element in tree.iter():
            if element.tag.split('}')[-1] in ('script', 'foreignObject', 'image'):
                raise ValueError(f'External/embedded active content not allowed: {path}')
            if any(k.lower().startswith('on') or k.endswith('href') for k in element.attrib):
                raise ValueError(f'Unexpected SVG behavior: {path}')
    for folder in ('scripts', 'tests', 'assets', 'docs', '.github'):
        for path in (root / folder).rglob('*'):
            if '.cache' in path.parts or path.name.startswith('preview') or path.suffix not in ('.py', '.md', '.json', '.svg', '.yml'):
                continue
            raw = path.read_bytes()
            raw.decode('utf-8')
            if raw.startswith(b'\xef\xbb\xbf') or b'\r' in raw:
                raise ValueError(f'Expected UTF-8 without BOM and LF: {path}')
    raw = (root / 'README.md').read_bytes()
    if raw.startswith(b'\xef\xbb\xbf') or b'\r' in raw:
        raise ValueError('README encoding/newline mismatch')
    print('PASS: snapshot, README, SVGs, local image references and UTF-8/LF validation.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--offline', action='store_true', help='Render the existing snapshot without any API calls')
    parser.add_argument('--cache-dir', help='Optional local setup cache; use a new directory for each data refresh')
    args = parser.parse_args()
    if args.check:
        check()
        return
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    replace_block(readme, START + '\n' + END)
    data = json.loads((ROOT / 'docs/profile-data.json').read_text(encoding='utf-8')) if args.offline else collect(GitHub(args.cache_dir))
    block, assets = generated(data)
    updated = replace_block(readme, block)
    # Finish all network requests and rendering before replacing published files.
    for content in assets.values():
        ET.fromstring(content)
    for name, content in assets.items():
        write(ROOT / 'assets/generated' / name, content)
    write(ROOT / 'docs/profile-data.json', json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    write(ROOT / 'README.md', updated)
    check()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
