
from typing import Any

from lilya.apps import Lilya
from lilya.responses import FileResponse
from lilya.routing import Path
from lilya.types import Scope
from lilya.ranges import ContentRanges

class CustomFileResponse(FileResponse):
    def get_content_ranges_and_multipart(
        self, scope: Scope, /, **kwargs: Any
    ) -> tuple[ContentRanges | None, bool]:
        kwargs.setdefault("enforce_asc", False)
        # unlimit the amount of requested ranges and do security later
        kwargs.setdefault("max_ranges", None if self.range_multipart_boundary else 1)
        content_ranges, multipart = super().get_content_ranges_and_multipart(scope, **kwargs)

        # check that ranges are not too small, resource abuse by using protocol overhead
        # Note: we have already a mitigation in place by allowing only strictly ascending orders even with enforce_asc=False
        # enforce_asc=False is more lenient by modifying the ranges
        for range_def in content_ranges.ranges:
            # ranges must be at least 50 bytes otherwise the whole response is returned
            if range_def.stop - range_def.start +1 <= 50:
                # returning (None, ...) causes a whole response to be returned instead of a partial response
                return None, False

        # allow unordered ranges
        # allow single range responses on multi range requests (spec violation some clients does not support)
        # by default multipart is used when a "," is in the range header
        return content_ranges, len(content_ranges.ranges) > 1

def home() -> CustomFileResponse:
    return CustomFileResponse(
        "files/something.csv",
        filename="something",
    )


app = Lilya(routes=[Path("/", home)])
