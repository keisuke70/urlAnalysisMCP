from mcp_server.server import analyze_company

def test_schema_only(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")   # simulate missing key
    result = analyze_company("https://example.com")
    assert set(result.keys()) == {"manufacturer", "email", "contact", "contact_url", "mail_body"}
    
    assert isinstance(result["manufacturer"], bool)
    assert result["email"] is None or isinstance(result["email"], str)
    assert isinstance(result["contact"], bool)
    assert result["contact_url"] is None or isinstance(result["contact_url"], str)
    assert isinstance(result["mail_body"], str)
