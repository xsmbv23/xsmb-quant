from verification.canonical_bounded_fixture import independent_quorum


def test_quorum_requires_two_distinct_source_identities():
    ok, ids = independent_quorum({"source_identities": ["ketqua16.net", "xsmb.com.vn"]})
    assert ok is True
    assert ids == ["ketqua16.net", "xsmb.com.vn"]


def test_declared_source_count_alone_cannot_create_quorum():
    ok, ids = independent_quorum({"source_count": 2})
    assert ok is False
    assert ids == []


def test_duplicate_source_identity_does_not_count_twice():
    ok, ids = independent_quorum({"source_identities": ["ketqua16.net", "ketqua16.net"]})
    assert ok is False
    assert ids == ["ketqua16.net"]
