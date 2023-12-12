from lilya.datastructures import URL


def test_url_structure():
    url = URL("https://example.org:123/path/to/somewhere?abc=123#anchor")
    assert url.scheme == "https"
    assert url.hostname == "example.org"
    assert url.port == 123
    assert url.netloc == "example.org:123"
    assert url.username is None
    assert url.password is None
    assert url.path == "/path/to/somewhere"
    assert url.query == "abc=123"
    assert url.fragment == "anchor"

    new = url.replace(scheme="http")
    assert new == "http://example.org:123/path/to/somewhere?abc=123#anchor"
    assert new.scheme == "http"

    new = url.replace(port=None)
    assert new == "https://example.org/path/to/somewhere?abc=123#anchor"
    assert new.port is None

    new = url.replace(hostname="example.com")
    assert new == "https://example.com:123/path/to/somewhere?abc=123#anchor"
    assert new.hostname == "example.com"

    ipv6_url = URL("https://[fe::2]:12345")
    new = ipv6_url.replace(port=8080)
    assert new == "https://[fe::2]:8080"

    new = ipv6_url.replace(username="username", password="password")
    assert new == "https://username:password@[fe::2]:12345"
    assert new.netloc == "username:password@[fe::2]:12345"

    ipv6_url = URL("https://[fe::2]")
    new = ipv6_url.replace(port=123)
    assert new == "https://[fe::2]:123"

    url = URL("http://u:p@host/")
    assert url.replace(hostname="bar") == URL("http://u:p@bar/")

    url = URL("http://u:p@host:80")
    assert url.replace(port=88) == URL("http://u:p@host:88")


def test_url_query_params():
    url = URL("https://example.org/path/?page=3")
    assert url.query == "page=3"

    url = url.include_query_params(page=4)
    assert str(url) == "https://example.org/path/?page=4"

    url = url.include_query_params(search="testing")
    assert str(url) == "https://example.org/path/?page=4&search=testing"

    url = url.replace_query_params(order="name")
    assert str(url) == "https://example.org/path/?order=name"

    url = url.remove_query_params("order")
    assert str(url) == "https://example.org/path/"


def test_hidden_password():
    url = URL("https://example.org/path/to/somewhere")
    assert repr(url) == "URL('https://example.org/path/to/somewhere')"

    url = URL("https://username@example.org/path/to/somewhere")
    assert repr(url) == "URL('https://username@example.org/path/to/somewhere')"

    url = URL("https://username:password@example.org/path/to/somewhere")
    assert repr(url) == "URL('https://username:********@example.org/path/to/somewhere')"
