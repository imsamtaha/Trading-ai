import json

import pytest

from app.dashboard.market_briefing import MarketBriefingService


@pytest.mark.parametrize(('title', 'category'), [
    ('Federal Reserve holds interest rates', 'MACRO'),
    ('الفيدرالي الأميركي يثبت أسعار الفائدة', 'MACRO'),
    ('ECB monetary policy announcement', 'MACRO'),
    ('البنك المركزي الأوروبي يخفض الفائدة', 'MACRO'),
    ('EUR/USD rises against the dollar', 'FX'),
    ('اليورو يتراجع مقابل الدولار', 'FX'),
    ('Gold prices increase', 'COMMODITIES'),
    ('أسعار الذهب ترتفع', 'COMMODITIES'),
    ('Brent oil falls', 'COMMODITIES'),
    ('النفط يتراجع', 'COMMODITIES'),
    ('Bitcoin gains 2%', 'DIGITAL_ASSETS'),
    ('بيتكوين ترتفع', 'DIGITAL_ASSETS'),
    ('Ethereum market update', 'DIGITAL_ASSETS'),
    ('سوق العملات الرقمية', 'DIGITAL_ASSETS'),
    ('Nasdaq stocks close higher', 'EQUITIES'),
    ('بورصة نيويورك والأسهم', 'EQUITIES'),
    ('S&P 500 advances', 'EQUITIES'),
    ('التضخم يرتفع', 'MACRO'),
    ('Football scores today', 'GENERAL'),
    ('Golden opportunity for school children', 'GENERAL'),
])
def test_bilingual_headlines_are_routed_without_paid_calls(monkeypatch, title, category):
    from app.dashboard.news_routing import NewsRouter
    monkeypatch.delenv('ATLAS_NEWS_ROUTING_ENABLED', raising=False)
    story = {'title': title, 'source_verified': True, 'fresh': True}
    result = NewsRouter().annotate([story])[0]
    assert result['routing']['category'] == category
    assert result['routing']['method'] == 'RULES'
    assert result['routing']['dispatch'] == 'METADATA_ONLY'
    assert story == {'title': title, 'source_verified': True, 'fresh': True}


def test_briefing_adds_routing_after_language_selection(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    service = MarketBriefingService()
    service._feed = lambda source: [{'title': 'أسعار الذهب ترتفع', 'url': 'https://www.bbc.com/arabic/a',
        'published_at': '2026-10-01T00:00:00+00:00', 'language': 'ar', 'source_verified': True}]
    stories = service.headlines(language='ar')
    assert len(stories) <= 3
    assert stories[0]['routing']['agent'] == 'commodities_analyst'
    assert stories[0]['title_ar'] == 'أسعار الذهب ترتفع'


def test_model_classifies_batch_once_and_preserves_provenance(monkeypatch):
    from app.dashboard.news_routing import NewsRouter
    monkeypatch.setenv('ATLAS_NEWS_ROUTING_ENABLED', 'true')
    calls = []
    def classify(payload):
        calls.append(payload)
        return json.dumps({'routes': [{'id': 0, 'category': 'FX'}]})
    router = NewsRouter(classify=classify)
    story = {'title': 'Currency outlook', 'source_verified': True, 'fresh': True, 'url': 'https://example.com/a'}
    first = router.annotate([story])[0]
    second = router.annotate([{**story, 'url': 'https://example.com/b'}])[0]
    assert first['routing']['category'] == 'FX'
    assert first['routing']['method'] == 'MODEL'
    assert second['url'] == 'https://example.com/b'
    assert second['routing']['category'] == 'FX'
    assert len(calls) == 1


@pytest.mark.parametrize('response', [
    'not json', '{"routes":[]}', '{"routes":[{"id":0,"category":"BUY"}]}',
    '{"routes":[{"id":true,"category":"FX"}]}',
    '{"routes":[{"id":3,"category":"FX"}]}',
    '{"routes":[{"id":0,"category":"FX"},{"id":0,"category":"MACRO"}]}',
])
def test_invalid_model_results_fall_back_without_paid_retry(monkeypatch, response):
    from app.dashboard.news_routing import NewsRouter
    monkeypatch.setenv('ATLAS_NEWS_ROUTING_ENABLED', 'true')
    calls = []
    def classify(payload):
        calls.append(payload)
        return response
    router = NewsRouter(classify=classify)
    story = {'title': 'Gold prices', 'source_verified': True, 'fresh': True}
    for _ in range(2):
        route = router.annotate([story])[0]['routing']
        assert route['category'] == 'COMMODITIES'
        assert route['method'] == 'RULES_FALLBACK'
    assert len(calls) == 1


def test_stale_and_unverified_news_never_reach_model(monkeypatch):
    from app.dashboard.news_routing import NewsRouter
    monkeypatch.setenv('ATLAS_NEWS_ROUTING_ENABLED', 'true')
    def classify(payload):
        pytest.fail('Ineligible headline reached the paid provider')
    results = NewsRouter(classify=classify).annotate([
        {'title': 'Gold', 'source_verified': True, 'fresh': False},
        {'title': 'Bitcoin', 'source_verified': False, 'fresh': True},
    ])
    assert [item['routing']['method'] for item in results] == ['RULES', 'RULES']


def test_provider_failure_keeps_headline_available(monkeypatch):
    from app.dashboard.news_routing import NewsRouter
    monkeypatch.setenv('ATLAS_NEWS_ROUTING_ENABLED', 'true')
    def classify(payload):
        raise TimeoutError('provider unavailable')
    result = NewsRouter(classify=classify).annotate([
        {'title': 'النفط يتراجع', 'source_verified': True, 'fresh': True}])[0]
    assert result['title'] == 'النفط يتراجع'
    assert result['routing']['category'] == 'COMMODITIES'
    assert result['routing']['method'] == 'RULES_FALLBACK'
