from app.auth.routes import login_page


def test_google_login_uses_direct_id_token_flow_not_redirect_oauth():
    html = login_page().body.decode('utf-8')
    assert 'accounts.google.com/gsi/client' in html
    assert 'signInWithIdToken' in html
    assert "signInWithOAuth" not in html
    assert "redirectTo:location.origin+'/auth/callback'" not in html
