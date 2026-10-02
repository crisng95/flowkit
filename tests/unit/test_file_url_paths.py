"""file:// URL <-> local path conversion must work on every OS.

The pipeline stores local media as ``"file://" + str(path)``. On POSIX that
yields ``file:///tmp/x.mp4`` which ``urlparse().path`` reads back fine. On
Windows it yields ``file://C:\\Temp\\x.mp4`` — ``urlparse`` puts ``C:\\Temp\\x.mp4``
in *netloc* and leaves ``path`` empty, so every ``Path(parsed.path)`` caller
concluded the file did not exist and fell through to an HTTP download.
"""
import sys
from pathlib import Path

import pytest

from agent.utils.paths import file_url_to_path


def test_naive_file_url_from_str_path_roundtrips(tmp_path):
    f = tmp_path / "clip.mp4"
    f.write_bytes(b"x")
    assert file_url_to_path(f"file://{f}") == f


def test_rfc8089_file_url_from_as_uri_roundtrips(tmp_path):
    f = tmp_path / "x y.png"  # space -> %20 in as_uri()
    f.write_bytes(b"x")
    assert file_url_to_path(f.as_uri()) == f


def test_posix_style_file_url_is_accepted():
    p = file_url_to_path("file:///tmp/out.png")
    assert p == Path("/tmp/out.png")


def test_non_file_urls_and_empty_return_none():
    assert file_url_to_path("https://example.com/a.mp4") is None
    assert file_url_to_path("") is None
    assert file_url_to_path(None) is None


def test_plain_path_is_not_a_file_url(tmp_path):
    # Callers that accept bare paths handle that branch themselves.
    assert file_url_to_path(str(tmp_path / "a.mp4")) is None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows drive-letter form")
def test_windows_backslash_form_keeps_drive_letter():
    p = file_url_to_path(r"file://C:\Windows\Temp\x.png")
    assert p == Path(r"C:\Windows\Temp\x.png")
