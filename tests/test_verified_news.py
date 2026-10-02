from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from types import SimpleNamespace
from xml.sax.saxutils import escape

import pytest
import requests

from app.dashboard.market_briefing import MarketBriefingService, _arabic_headlines

FEEDS = {
    'https://www.federalreserve.gov/feeds/press_monetary.xml': ('FOMC holds rates at 4.25%', 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20261002a.htm'),
    'https://www.ecb.europa.eu/rss/press.html': ('ECB monetary policy statement', 'https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.example.en.html'),
    'https://feeds.bbci.co.uk/arabic/rss.xml': ('تطورات الأسواق وأسعار النفط', 'https://www.bbc.com/arabic/articles/example'),
}


def rss(title, url, published=None):
    date = published or format_datetime(datetime.now(timezone.utc)-timedelta(minutes=5))
    return f'<rss><channel><item><title>{escape(title)}</title><link>{escape(url)}</link><pubDate>{date}</pubDate></item></channel></rss>'.encode()


class FeedSession:
    def __init__(self):
        self.calls = []
        self.overrides = {}
        self.published = format_datetime(datetime.now(timezone.utc)-timedelta(minutes=5))

    def get(self, url, **kwargs):
        self.calls.append(url)
        value = self.overrides.get(url)
        if isinstance(value, Exception):
            raise value
        title, link = FEEDS.get(url, ('Untrusted legacy news', 'https://example.com/story'))
        return SimpleNamespace(content=value or rss(title, link, self.published), status_code=200, url=url,
                               raise_for_status=lambda: None)


@pytest.fixture(autouse=True)
def no_paid_translation(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    from app.dashboard.market_briefing import _TRANSLATION_CACHE
    _TRANSLATION_CACHE.clear()


def test_news_reads_verified_publishers_and_preserves_native_arabic():
    session = FeedSession()
    stories = MarketBriefingService(session=session).headlines()
    assert set(session.calls) == set(FEEDS)
    assert {s['source_id'] for s in stories} == {'federal_reserve', 'ecb', 'bbc_arabic'}
    assert all(s['source_verified'] for s in stories)
    arabic = next(s for s in stories if s['source_id'] == 'bbc_arabic')
    assert arabic['title_ar'] == 'تطورات الأسواق وأسعار النفط'
    assert arabic['translation_status'] == 'ORIGINAL_ARABIC'
    assert arabic['freshness'] == 'FRESH'


def test_news_partial_failure_keeps_working_sources():
    session = FeedSession()
    session.overrides[next(iter(FEEDS))] = requests.Timeout('offline')
    stories = MarketBriefingService(session=session).headlines()
    assert {s['source_id'] for s in stories} == {'ecb', 'bbc_arabic'}


@pytest.mark.parametrize('url', ['javascript:alert(1)', 'https://evil.example/story', 'https://www.ecb.europa.eu.evil.example/story', 'https://user@www.ecb.europa.eu/story'])
def test_news_rejects_untrusted_article_links(url):
    session = FeedSession()
    session.overrides['https://www.ecb.europa.eu/rss/press.html'] = rss('Bad link', url)
    stories = MarketBriefingService(session=session).headlines()
    assert all(s.get('source_id') != 'ecb' for s in stories)


@pytest.mark.parametrize('date', ['not-a-date', format_datetime(datetime.now(timezone.utc)+timedelta(days=1))])
def test_news_rejects_unknown_and_future_publication_dates(date):
    session = FeedSession()
    session.overrides['https://www.ecb.europa.eu/rss/press.html'] = rss('ECB statement', FEEDS['https://www.ecb.europa.eu/rss/press.html'][1], date)
    assert all(s.get('source_id') != 'ecb' for s in MarketBriefingService(session=session).headlines())


def test_news_old_statements_are_not_marked_current():
    session = FeedSession()
    session.overrides['https://www.ecb.europa.eu/rss/press.html'] = rss('Old statement', FEEDS['https://www.ecb.europa.eu/rss/press.html'][1], format_datetime(datetime.now(timezone.utc)-timedelta(days=10)))
    story = next(s for s in MarketBriefingService(session=session).headlines() if s.get('source_id') == 'ecb')
    assert story['freshness'] == 'STALE'
    assert story['fresh'] is False


def test_news_cache_rechecks_age_and_does_not_refetch(monkeypatch):
    session = FeedSession()
    service = MarketBriefingService(session=session)
    first = service.headlines()
    second = service.headlines()
    assert first == second
    assert len(session.calls) == 3


def test_missing_translation_has_explicit_status():
    story = _arabic_headlines([{'title': 'FOMC holds rates at 4.25%', 'url': 'https://www.federalreserve.gov/a'}])[0]
    assert story['translation_status'] == 'UNAVAILABLE'
    assert not story.get('title_ar')
    assert story['title_en'] == 'FOMC holds rates at 4.25%'


def translation_client(monkeypatch, output, captured):
    import openai
    def create(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(output_text=output)
    monkeypatch.setattr(openai, 'OpenAI', lambda **kwargs: SimpleNamespace(responses=SimpleNamespace(create=create)))
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')


def test_translation_preserves_original_and_reuses_text_without_wrong_attribution(monkeypatch):
    captured = []
    translation_client(monkeypatch, '{"titles":["أبقى FOMC الفائدة عند 4.25%"]}', captured)
    a = _arabic_headlines([{'title': 'FOMC holds rates at 4.25%', 'url': 'https://www.federalreserve.gov/a'}])[0]
    b = _arabic_headlines([{'title': 'FOMC holds rates at 4.25%', 'url': 'https://www.federalreserve.gov/b'}])[0]
    assert a['title_ar'] == 'أبقى FOMC الفائدة عند 4.25%'
    assert b['url'].endswith('/b')
    assert b['translation_status'] == 'TRANSLATED'
    assert len(captured) == 1
    assert captured[0]['store'] is False


@pytest.mark.parametrize('output', ['{"titles":["الفائدة 5.25%"]}', '{"titles":["Still English 4.25%"]}', '{"titles":[null]}', '{"titles":[]}'])
def test_translation_rejects_changed_numbers_or_invalid_arabic(monkeypatch, output):
    translation_client(monkeypatch, output, [])
    story = _arabic_headlines([{'title': 'FOMC holds rates at 4.25%'}])[0]
    assert not story.get('title_ar')
    assert story['translation_status'] == 'UNAVAILABLE'


def test_arabic_mode_falls_back_to_three_native_stories_without_translation_key():
    session = FeedSession()
    session.overrides['https://feeds.bbci.co.uk/arabic/rss.xml'] = b'<rss><channel>' + b''.join(
        rss('تطورات الأسواق '+str(i), f'https://www.bbc.com/arabic/articles/story{i}').split(b'<channel>')[1].split(b'</channel>')[0]
        for i in range(8)) + b'</channel></rss>'
    stories = MarketBriefingService(session=session).headlines(limit=20)
    assert len(stories) == 3
    assert all(s.get('title_ar') for s in stories)
    assert all(s['translation_status'] == 'ORIGINAL_ARABIC' for s in stories)


def test_news_api_and_asset_work_in_dashboard_only_mode(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.dashboard import market_briefing as module
    service = MarketBriefingService(session=FeedSession())
    monkeypatch.setattr(service, 'market_board', lambda: [])
    monkeypatch.setattr(module, '_service', service)
    monkeypatch.setenv('ATLAS_DASHBOARD_ONLY', 'true')
    monkeypatch.setenv('ATLAS_MARKET_DATA_ENABLED', 'true')
    with TestClient(app) as client:
        assert client.get('/assets/atlas-news.js').status_code == 200
        body = client.get('/dashboard/market-briefing').json()
        assert body['language'] == 'ar'
        assert len(body['headlines']) == 3
        assert body['news_status'] == 'ONLINE'
        assert client.get('/dashboard/market-briefing?language=en').json()['language'] == 'en'
        assert client.get('/dashboard/market-briefing?language=fr').status_code == 422
        assert client.post('/mt5/test-order').status_code == 403


def test_cached_news_publication_age_is_rechecked(monkeypatch):
    from app.dashboard import market_briefing as module
    clock = {'now': datetime.now(timezone.utc)}
    class ClockDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock['now']
    monkeypatch.setattr(module, 'datetime', ClockDateTime)
    monkeypatch.setenv('ATLAS_NEWS_FRESH_SECONDS', '600')
    session = FeedSession()
    service = MarketBriefingService(session=session)
    assert all(s['fresh'] for s in service.headlines())
    clock['now'] += timedelta(minutes=15)
    assert all(s['freshness'] == 'STALE' for s in service.headlines())
    assert len(session.calls) == 3


def test_arabic_fallback_preserves_successfully_translated_official_news(monkeypatch):
    session = FeedSession()
    session.overrides['https://feeds.bbci.co.uk/arabic/rss.xml'] = b'<rss><channel>' + b''.join(
        rss('أخبار الأسواق '+str(i), f'https://www.bbc.com/arabic/articles/story{i}').split(b'<channel>')[1].split(b'</channel>')[0]
        for i in range(3)) + b'</channel></rss>'
    translation_client(monkeypatch, '{"titles":["أبقى FOMC الفائدة عند 4.25%","invalid English"]}', [])
    stories = MarketBriefingService(session=session).headlines()
    assert len(stories) == 3
    assert all(s['title_ar'] for s in stories)
    assert any(s['source_id'] == 'federal_reserve' and s['translation_status'] == 'TRANSLATED' for s in stories)


@pytest.mark.parametrize('output', ['{"titles":["invalid"]}', '{"titles":["تراجع السوق +2.5%"]}'])
def test_failed_translation_is_cached_to_avoid_repeated_paid_requests(monkeypatch, output):
    calls=[]
    translation_client(monkeypatch, output, calls)
    for i in range(3):
        _arabic_headlines([{'title':'Market falls -2.5%'}])
    assert len(calls) == 1


def test_translation_cannot_reverse_a_signed_market_move(monkeypatch):
    translation_client(monkeypatch, '{"titles":["تحرك السوق +2.5%"]}', [])
    result = _arabic_headlines([{'title':'Market moves -2.5%'}])[0]
    assert result['translation_status'] == 'UNAVAILABLE'
    assert not result.get('title_ar')
