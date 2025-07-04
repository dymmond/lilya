import pytest

from lilya.ranges import Range, parse_range_value


@pytest.mark.parametrize(
    "byterange,expected,strict_fails",
    [
        pytest.param("bytes=1,2,3", [Range(1, 3)], False, id="consecutive"),
        pytest.param("bytes=1,1,1", [Range(1, 1)], True, id="single_byte_ranges"),
        pytest.param(
            "bytes=1,0-90,1, 10-20, 4-8", [Range(0, 90)], True, id="drop_overlapping_ranges"
        ),
        pytest.param(
            "bytes=1, 10-20, 4-8",
            [Range(1, 1), Range(4, 8), Range(10, 20)],
            True,
            id="ordering",
        ),
        pytest.param(
            "bytes=1, 4-8, 10-200",
            [Range(1, 1), Range(4, 8), Range(10, 100)],
            False,
            id="clamp_overshooting",
        ),
    ],
)
def test_merge(byterange, expected, strict_fails):
    assert parse_range_value(byterange, 100, enforce_asc=False).ranges == expected
    if strict_fails:
        assert parse_range_value(byterange, 100, enforce_asc=True) is None
    else:
        assert parse_range_value(byterange, 100, enforce_asc=True).ranges == expected


@pytest.mark.parametrize(
    "byterange,expected,strict_fails",
    [
        pytest.param(
            "bytes=1,2,3", [Range(1, 1), Range(2, 2), Range(3, 3)], False, id="consecutive"
        ),
        pytest.param("bytes=1,1,1", [Range(1, 1)], True, id="single_byte_ranges"),
        pytest.param(
            "bytes=1,0-90,1, 10-20, 4-8", [Range(0, 90)], True, id="drop_overlapping_ranges"
        ),
        pytest.param(
            "bytes=1, 4-8, 10-200",
            [Range(1, 1), Range(4, 8), Range(10, 100)],
            False,
            id="clamp_overshooting",
        ),
    ],
)
def test_nomerge(byterange, expected, strict_fails):
    assert (
        parse_range_value(byterange, 100, enforce_asc=False, merge_ranges=False).ranges == expected
    )
    if strict_fails:
        assert parse_range_value(byterange, 100, enforce_asc=True, merge_ranges=False) is None
    else:
        assert (
            parse_range_value(byterange, 100, enforce_asc=True, merge_ranges=False).ranges
            == expected
        )


@pytest.mark.parametrize(
    "extra",
    [
        pytest.param({}, id="none"),
        pytest.param({"merge_ranges": True}, id="merge"),
        pytest.param({"merge_ranges": False}, id="nomerge"),
    ],
)
def test_max_ranges_and_units(extra):
    assert parse_range_value("bytes=1,2,3", max_values=100, **extra) is not None
    assert parse_range_value("bytes=1,2,3", max_values=100, max_ranges=1, **extra) is None
    # test other units
    assert (
        parse_range_value("unicorns=1,2,3", max_values={"unicorns": 100}, max_ranges=1, **extra)
        is None
    )
    assert parse_range_value("bytes=1,2,3", max_values={"unicorns": 100}, **extra) is None
