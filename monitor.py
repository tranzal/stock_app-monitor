"""Public, independent availability checks. No service credentials are used."""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler

ORIGIN = 'https://stockly-tranzal.duckdns.org'
MARKER = '<!-- stockly-independent-monitor-v1 -->'
TITLE = '[STOCKLY] 서비스 접속 장애'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe():
    opener = build_opener(NoRedirect())
    for path, expected in (('/', 200), ('/v1/auth/me', 401)):
        try:
            with opener.open(Request(ORIGIN + path, headers={
                    'User-Agent': 'StocklyIndependentMonitor/1.0'}), timeout=8) as response:
                status = response.status
        except HTTPError as error:
            status = error.code
            error.close()
        except (OSError, ValueError):
            return False
        if status != expected:
            return False
    return True


def api(method, path, body=None):
    # A job-scoped GitHub token can reach only this exact GitHub repository.
    repository = os.environ.get('GITHUB_REPOSITORY', '')
    if repository != 'tranzal/stock_app-monitor':
        raise ValueError('Unexpected monitoring repository')
    token = os.environ.get('GITHUB_TOKEN', '')
    if not token or not re.fullmatch(r'/issues(?:\?[A-Za-z0-9_=&]+|/\d+(?:/comments)?)?', path):
        raise ValueError('Invalid monitoring API request')
    request = Request('https://api.github.com/repos/' + repository + path,
        data=None if body is None else json.dumps(body).encode(), method=method,
        headers={'Accept': 'application/vnd.github+json',
            'Authorization': 'Bearer ' + token, 'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json', 'User-Agent': 'StocklyIndependentMonitor/1.0'})
    with build_opener(NoRedirect()).open(request, timeout=15) as response:
        return json.loads(response.read(1024 * 1024))


def incidents():
    found = []
    for page in range(1, 11):
        rows = api('GET', f'/issues?state=open&per_page=100&page={page}')
        for row in rows:
            if (row.get('title') == TITLE and MARKER in (row.get('body') or '')
                    and row.get('user', {}).get('login') == 'github-actions[bot]'
                    and not row.get('pull_request')):
                found.append(row['number'])
        if len(rows) < 100:
            return found
    raise RuntimeError('Issue query limit reached')


def run():
    opened = incidents()
    healthy = probe()
    if healthy and opened:
        time.sleep(15)
        healthy = probe()  # Recovery must be observed twice.
        if not healthy:
            print('Recovery not yet confirmed; existing incident retained.')
            return 1
    elif not healthy:
        # Brief deployment or restart interruptions do not immediately alert.
        for _ in range(2):
            time.sleep(20)
            if probe():
                print('Transient interruption; no new incident.')
                return 0
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    if healthy:
        for number in opened:
            api('POST', f'/issues/{number}/comments', {
                'body': f'복구 확인: {now}\n공개 웹 페이지와 로그인 보호 응답을 두 번 확인했습니다.'})
            api('PATCH', f'/issues/{number}', {'state': 'closed', 'state_reason': 'completed'})
        print('Public site and protected authentication response are available.')
        return 0
    if not opened:
        api('POST', '/issues', {'title': TITLE,
            'body': f'{MARKER}\n\n접속 장애 확인: {now}\n\n공개 주소 {ORIGIN} 에서 '
                '웹 응답 또는 로그인 보호 응답이 연속 3회 정상적으로 확인되지 않았습니다. '
                'PC·인터넷·공유기·서비스 상태를 확인하세요. 복구가 두 번 확인되면 이 이슈가 자동으로 닫힙니다.\n\n'
                '계정·시세·접속 기록·서버 내부 정보는 수집하거나 공개하지 않습니다.',
            'assignees': ['tranzal']})
    print('Public availability check failed; incident recorded without private diagnostics.')
    return 1


if __name__ == '__main__':
    try:
        raise SystemExit(run())
    except Exception:
        # GitHub API exceptions must not echo authorization headers or payloads.
        print('Independent monitor could not complete. Review workflow configuration.')
        raise SystemExit(2)
