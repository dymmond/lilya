import io
import os
import tempfile

from lilya.apps import Lilya
from lilya.contrib.responses.files import send_file
from lilya.routing import Path
from lilya.testclient import TestClient


def create_temp_file(content: bytes, suffix=".txt"):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(content)
    tmp.close()
    return tmp.name


def test_no_content_disposition_for_inline_files(test_client_factory):
    """
    Ensure that send_file() does not set Content-Disposition
    when as_attachment=False.
    """
    tmp_path = create_temp_file(b"inline content", ".txt")

    async def endpoint(request):
        return send_file(tmp_path)

    app = Lilya(routes=[Path("/inline", endpoint)])
    client = TestClient(app)

    response = client.get("/inline")
    assert response.status_code == 200
    assert "content-disposition" not in response.headers
    assert response.text == "inline content"

    os.remove(tmp_path)


def test_content_disposition_for_attachment_with_correct_filename(test_client_factory):
    """
    Ensure that send_file() sets a clean Content-Disposition header
    when as_attachment=True, with the exact filename passed.
    """
    tmp_path = create_temp_file(b"download data", ".txt")
    custom_filename = "Lilya_export.xlsx"

    async def endpoint(request):
        file_like = io.BytesIO(b"dummy content")
        return send_file(
            file_like,
            as_attachment=True,
            attachment_filename=custom_filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    app = Lilya(routes=[Path("/download", endpoint)])
    client = TestClient(app)

    response = client.get("/download")
    assert response.status_code == 200

    # Ensure header exists
    content_disp = response.headers.get("content-disposition")
    assert content_disp is not None, "Content-Disposition header missing"
    assert content_disp.startswith("attachment;")

    # Ensure filename is exactly as expected — no underscores, no wrapping
    assert f'filename="{custom_filename}"' in content_disp, content_disp

    os.remove(tmp_path)
