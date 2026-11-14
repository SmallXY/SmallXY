import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_profile as p


def repo(name='SmallXY/one', stars=1, scope='personal', lead=False, **extra):
    return {'full_name': name, 'html_url': 'https://github.com/' + name,
            'description': 'A < B & 中文项目', 'stargazers_count': stars,
            'fork': False, 'archived': False, 'created_at': '2024-01-01T00:00:00Z',
            'pushed_at': '2025-01-01T00:00:00Z', 'language': None, 'scope': scope,
            'contribution': {'commits': 5, 'top_commits': 5, 'is_lead': lead,
                             'tied': False, 'leaders': ['SmallXY']}, **extra}


def snapshot():
    return {'updated_at': '2026-11-14T00:00:00Z', 'account_created_at': '2020-03-17T00:00:00Z',
            'personal_repositories': [repo()], 'organization_repositories': [],
            'external_contribution_evidence': {}, 'public_organizations': []}


class ProfileTests(unittest.TestCase):
    def test_leading_and_tied_contributors(self):
        result = p.contribution([{'login': 'smallxy', 'contributions': 5}, {'login': 'peer', 'contributions': 5}])
        self.assertTrue(result['is_lead'])
        self.assertTrue(result['tied'])
        self.assertFalse(p.contribution([{'login': 'SmallXY', 'contributions': 4}, {'login': 'peer', 'contributions': 5}])['is_lead'])
        self.assertFalse(p.contribution([])['is_lead'])
        self.assertFalse(p.contribution([{'login': 'peer', 'contributions': 5}])['is_lead'])

    def test_ranking_scope_and_stable_ties(self):
        data = snapshot()
        data['personal_repositories'] += [repo('SmallXY/fork', 500, fork=True), repo('SmallXY/old', 50, archived=True), repo('SmallXY/SmallXY', 70)]
        data['organization_repositories'] = [repo('Org/leader', 2, 'organization', True), repo('Org/other', 600, 'organization')]
        top, latest, stats = p.selections(data)
        self.assertEqual([r['full_name'] for r in top], ['Org/leader', 'SmallXY/one'])
        self.assertEqual(dict(stats)['作品获星'], 53)
        self.assertEqual(dict(stats)['主要贡献组织项目'], 1)
        data['personal_repositories'].append(repo('SmallXY/newer', 1, pushed_at='2026-01-01T00:00:00Z'))
        self.assertEqual(p.selections(data)[0][1]['full_name'], 'SmallXY/newer')

    def test_latest_uses_created_not_updated(self):
        data = snapshot()
        data['personal_repositories'].append(repo('SmallXY/new', created_at='2026-01-01T00:00:00Z', pushed_at='2024-01-01T00:00:00Z'))
        self.assertEqual(p.selections(data)[1][0]['full_name'], 'SmallXY/new')

    def test_pages_include_every_page_and_empty_response(self):
        api = p.GitHub()
        api.get = Mock(side_effect=[list(range(100)), [100]])
        self.assertEqual(len(api.pages('/test')), 101)
        self.assertEqual(api.get.call_args.kwargs['page'], 2)
        api.get = Mock(return_value=[])
        self.assertEqual(api.pages('/empty'), [])

    def test_search_incomplete_and_cap_fail_closed(self):
        for total, incomplete in [(1001, False), (1, True)]:
            api = p.GitHub()
            api.get = Mock(return_value={'total_count': total, 'incomplete_results': incomplete, 'items': []})
            with self.assertRaises(ValueError):
                api.search('commits', 'author:SmallXY')

    def test_search_pagination_and_changed_total(self):
        api = p.GitHub()
        api.get = Mock(side_effect=[{'total_count': 101, 'incomplete_results': False, 'items': list(range(100))},
                                    {'total_count': 101, 'incomplete_results': False, 'items': [100]}])
        self.assertEqual(len(api.search('commits', 'query')), 101)
        api.get = Mock(side_effect=[{'total_count': 101, 'incomplete_results': False, 'items': list(range(100))},
                                    {'total_count': 102, 'incomplete_results': False, 'items': [100]}])
        with self.assertRaises(ValueError):
            api.search('commits', 'query')

    def test_collection_deduplicates_external_evidence(self):
        api = Mock()
        api.get.return_value = {'created_at': '2020-03-17T00:00:00Z'}
        api.pages.side_effect = [[repo()], [{'login': 'Org'}], [repo('Org/project', scope='organization')],
                                 [{'login': 'SmallXY', 'contributions': 8}]]
        api.search.side_effect = [[{'repository': {'full_name': 'Org/project', 'fork': False}, 'html_url': 'https://github.com/Org/project/commit/one'},
                                  {'repository': {'full_name': 'Org/project', 'fork': False}, 'html_url': 'https://github.com/Org/project/commit/two'},
                                  {'repository': {'full_name': 'Other/fork', 'fork': True}, 'html_url': 'https://github.com/Other/fork/commit/a'}],
                                 [{'repository_url': p.API + '/repos/Org/project', 'html_url': 'https://github.com/Org/project/pull/1'}]]
        data = p.collect(api)
        self.assertEqual(len(data['external_contribution_evidence']), 1)
        self.assertTrue(all(data['external_contribution_evidence']['Org/project'].values()))

    def test_xml_escaping_long_descriptions_and_empty_data(self):
        value = repo(description='<script>alert("x")</script> & ' + '非常长的描述' * 100)
        parsed = ET.fromstring(p.render_repo(value, 1))
        self.assertFalse(any(x.tag.endswith('script') for x in parsed.iter()))
        self.assertLessEqual(len(p.wrap(value['description'], 48, 2)), 2)
        self.assertIn('&#124;', p.md('a|b'))
        data = snapshot()
        data['personal_repositories'] = []
        content, assets = p.generated(data)
        self.assertIn('暂时没有', content)
        self.assertEqual(len(assets), 2)

    def test_update_preserves_handwritten_sections_and_is_deterministic(self):
        data = snapshot()
        first = p.generated(data)
        self.assertEqual(first, p.generated(copy.deepcopy(data)))
        original = 'BEFORE\n' + p.START + '\nold\n' + p.END + '\nAFTER'
        updated = p.replace_block(original, first[0])
        self.assertTrue(updated.startswith('BEFORE\n'))
        self.assertTrue(updated.endswith('\nAFTER'))
        self.assertEqual(updated, p.replace_block(updated, first[0]))
        for broken in ['', p.END + p.START, p.START + p.START + p.END]:
            with self.assertRaises(ValueError):
                p.replace_block(broken, first[0])

    def test_fetch_failure_never_writes_published_data(self):
        with patch.object(sys, 'argv', ['update_profile.py']), patch.object(p, 'collect', side_effect=RuntimeError('API down')), patch.object(p, 'write') as output:
            with self.assertRaises(RuntimeError):
                p.main()
            output.assert_not_called()


if __name__ == '__main__':
    unittest.main()
