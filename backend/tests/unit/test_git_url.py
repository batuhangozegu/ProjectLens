import pytest

from projectlens.git.url import InvalidRepositoryUrl, validate_repository_url


@pytest.mark.parametrize(
    "value",
    [
        "http://github.com/owner/repo",
        "ssh://github.com/owner/repo",
        "git@github.com:owner/repo.git",
        "file:///tmp/repo",
        "../repo",
        "C:\\repo",
        "https://gitlab.com/owner/repo",
        "https://github.com.evil.io/owner/repo",
        "https://github.com@evil.com/owner/repo",
        "https://user:pass@github.com/owner/repo",
        "https://github.com:443/owner/repo",
        "https://github.com/owner/repo?x=1",
        "https://github.com/owner/repo#readme",
        "https://github.com/owner/repo/tree/main",
        "https://github.com/owner/repo/blob/main/file.py",
        "https://github.com//repo",
        "https://github.com/owner/",
        "https://github.com/-owner/repo",
        "https://github.com/owner/-repo",
        "https://github.com/owner/repo name",
        "https://github.com/owner/repo\n.git",
        "https://github.com/ownér/repo",
        "https://xn--gthub-9za.com/owner/repo",
        "https://github.com/" + "o" * 40 + "/repo",
        "https://github.com/owner/" + "r" * 101,
        "https://github.com/owner/repo.git/extra",
        "https://github.com/owner/repo//",
    ],
)
def test_rejects_unsafe_or_noncanonical_urls(value):
    with pytest.raises(InvalidRepositoryUrl):
        validate_repository_url(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://github.com/owner/repo", "https://github.com/owner/repo"),
        ("https://github.com/owner/repo.git", "https://github.com/owner/repo"),
        ("https://github.com/owner/repo/", "https://github.com/owner/repo"),
        ("https://github.com/owner/repo.git/", "https://github.com/owner/repo"),
    ],
)
def test_normalizes_allowed_urls(value, expected):
    assert validate_repository_url(value) == (expected, "owner", "repo")


@pytest.mark.parametrize("value", [None, "", 42])
def test_requires_a_nonempty_string(value):
    with pytest.raises(InvalidRepositoryUrl):
        validate_repository_url(value)
