from dataclasses import dataclass, field
from typing import NamedTuple


class Range(NamedTuple):
    start: int
    stop: int


@dataclass
class ContentRanges:
    unit: str
    max_value: int
    size: int = 0
    ranges: list[Range] = field(default_factory=list)


def _parse_range_intern(rangedef: str, max_value: int) -> Range:
    # don't hick up on whitespaces
    rangedef = rangedef.strip()
    if rangedef.startswith("-"):
        return Range(start=max_value + int(rangedef), stop=max_value)
    elif rangedef.endswith("-"):
        return Range(start=int(rangedef[:-1]), stop=max_value)
    else:
        # this will cause an error in case of a wrong format, e.g.: 3--3
        # this accepts also defs like 3
        splitted = rangedef.rsplit("-", 1)
        return Range(start=int(splitted[0]), stop=int(splitted[-1]))


def _parse_range(rangedef: str, max_value: int) -> Range:
    range_val = _parse_range_intern(rangedef, max_value)
    if range_val.start > range_val.stop:
        raise ValueError("Invalid range, stop < start")
    if range_val.start < 0:
        raise ValueError("Invalid range, start negative")
    if range_val.stop > max_value:
        raise ValueError("Invalid range, stop bigger than max_value")

    return range_val


def parse_range_value(
    header_value: bytes | str | None,
    max_values: dict[str, int] | int,
    *,
    enforce_asc: bool = True,
    max_ranges: int | None = None,
) -> None | ContentRanges:
    """
    Parse a value in the format of http-range.

    Kwargs:
        header_value: A value in the format of http-range.
                      In case of some custom protocols without the `bytes=` prefix, you can drop in
                      `max_values={'': value}`
        max_values: A dict with maximal values for any unit. You can just pass an int for the default bytes unit.
        enforce_asc: Enforce that the ranges are consecutive ascending. Otherwise they are sorted and checked afterwards.
        max_ranges: Optional early bail out.

    Return:
        ContentRanges, with ascending ordered ranges.
    """
    # WARNING: max_values is content-length -1 for bytes
    # max_values == int is shortcut for {"bytes": value}
    if not header_value:
        return None
    if not isinstance(header_value, str):
        header_value = header_value.decode("utf8")
    if isinstance(max_values, int):
        max_values = {"bytes": max_values}
    if "=" not in header_value:
        unit, rest = "", header_value
    else:
        unit, rest = header_value.split("=", 1)
    if unit not in max_values:
        return None
    max_value = max_values[unit]
    crange: ContentRanges = ContentRanges(unit=unit, max_value=max_value)
    last_stop: int = -1
    succeeding_count: int = 1
    for rangedef in rest.split(","):
        if max_ranges is not None and succeeding_count > max_ranges:
            return None
        succeeding_count += 1
        try:
            range_val = _parse_range(rangedef, max_value)
        except ValueError:
            return None
        if enforce_asc and range_val.start <= last_stop:
            return None
        last_stop = range_val.stop
        if last_stop > max_value:
            last_stop = range_val.stop = max_value
        if enforce_asc:
            crange.size += range_val.stop - range_val.start + 1

        crange.ranges.append(range_val)

    if not enforce_asc:
        old_ranges = crange.ranges
        old_ranges.sort()
        crange.ranges = []
        # check that ranges are ascending afterwards, otherwise we have the danger of
        # malicious clients requesting the same range again and again
        last_range: Range = None
        for range_val in old_ranges:
            # ensure ascending order
            if last_range is not None and range_val.start <= last_range.stop:
                range_val.start = min(last_range.stop + 1, max_value)
            # only add if range is valid
            if range_val.stop >= range_val.start:
                crange.ranges.append(range_val)
                crange.size += range_val.stop - range_val.start + 1
                last_range = range_val

    return crange
