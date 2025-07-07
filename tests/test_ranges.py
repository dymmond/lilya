import pytest

from lilya.exceptions import ContentRangeNotSatisfiable
from lilya.ranges import Range, parse_range_value


@pytest.mark.parametrize(
    "byterange,expected,expected_size,strict_fails",
    [
        pytest.param("bytes=1,2,3", [Range(1, 3)], 3, False, id="consecutive"),
        pytest.param("bytes=1,1,1", [Range(1, 1)], 1, True, id="single_byte_ranges"),
        pytest.param(
            "bytes=1,0-90,1, 10-20, 4-8", [Range(0, 90)], 91, True, id="drop_overlapping_ranges"
        ),
        pytest.param(
            "bytes=1, 10-20, 4-8",
            [Range(1, 1), Range(4, 8), Range(10, 20)],
            17,
            True,
            id="ordering",
        ),
    ],
)
def test_merge(byterange, expected, expected_size, strict_fails):
    assert parse_range_value(byterange, 100, enforce_asc=False).ranges == expected
    assert parse_range_value(byterange, 100, enforce_asc=False).size == expected_size
    if strict_fails:
        assert parse_range_value(byterange, 100, enforce_asc=True) is None
    else:
        assert parse_range_value(byterange, 100, enforce_asc=True).ranges == expected
        assert parse_range_value(byterange, 100, enforce_asc=True).size == expected_size


@pytest.mark.parametrize(
    "byterange,expected,expected_size,strict_fails",
    [
        pytest.param(
            "bytes=1,2,3", [Range(1, 1), Range(2, 2), Range(3, 3)], 3, False, id="consecutive"
        ),
        pytest.param("bytes=1,1,1", [Range(1, 1)], 1, True, id="single_byte_ranges"),
        pytest.param(
            "bytes=1,0-90,1, 10-20, 4-8", [Range(0, 90)], 91, True, id="drop_overlapping_ranges"
        ),
    ],
)
def test_nomerge(byterange, expected, expected_size, strict_fails):
    assert (
        parse_range_value(byterange, 100, enforce_asc=False, merge_ranges=False).ranges == expected
    )
    assert (
        parse_range_value(byterange, 100, enforce_asc=False, merge_ranges=False).size
        == expected_size
    )
    if strict_fails:
        assert parse_range_value(byterange, 100, enforce_asc=True, merge_ranges=False) is None
    else:
        assert (
            parse_range_value(byterange, 100, enforce_asc=True, merge_ranges=False).ranges
            == expected
        )
        assert (
            parse_range_value(byterange, 100, enforce_asc=True, merge_ranges=False).size
            == expected_size
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


@pytest.mark.parametrize(
    "byterange,unit,size",
    [
        pytest.param(
            "bytes=1, 4-8, 10-200",
            "bytes",
            101,
            id="fail_overshooting_ordered",
        ),
        pytest.param(
            "bytes=101",
            "bytes",
            101,
            id="fail_overshooting_single_val",
        ),
        pytest.param(
            "bytes=10-200,1, 4-8",
            "bytes",
            101,
            id="fail_overshooting_unordered",
        ),
        pytest.param(
            "unicorns=10",
            "unicorns",
            1,
            id="fail_overshooting_other_unit",
        ),
    ],
)
def test_unsatisfiable(byterange, unit, size):
    with pytest.raises(ContentRangeNotSatisfiable) as exc_info:
        parse_range_value(byterange, max_values={"bytes": 100, "unicorns": 0}, enforce_asc=False)
    assert exc_info.value.unit == unit
    assert exc_info.value.size == size
    with pytest.raises(ContentRangeNotSatisfiable) as exc_info:
        parse_range_value(byterange, max_values={"bytes": 100, "unicorns": 0})
    assert exc_info.value.unit == unit
    assert exc_info.value.size == size
