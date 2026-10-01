import hashlib
import io
import json
import re
import threading

import pytest

from mispr import levels, models, settings, setup
from mispr.models import ModelSpec


# --- settings ----------------------------------------------------------------------

class TestSettings:
    def test_defaults_when_file_missing(self):
        s = settings.load()
        assert s.incognito is False and s.cleanup is True and s.onboarded is False

    def test_save_then_load_roundtrip(self):
        settings.save(settings.Settings(incognito=True, cleanup=False))
        s = settings.load()
        assert s.incognito is True and s.cleanup is False

    def test_save_creates_parent_folders(self):
        assert not settings.SETTINGS_PATH.parent.exists()
        settings.save(settings.Settings())
        assert settings.SETTINGS_PATH.exists()

    def test_save_creates_missing_grandparent_folders(self, monkeypatch, tmp_path):
        monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "a" / "b" / "c" / "settings.json")
        settings.save(settings.Settings())
        assert settings.SETTINGS_PATH.exists()

    def test_save_twice_overwrites(self):
        settings.save(settings.Settings(incognito=True))
        settings.save(settings.Settings(incognito=False))
        assert settings.load().incognito is False

    def test_saved_file_is_human_readable(self):
        settings.save(settings.Settings())
        assert settings.SETTINGS_PATH.read_text() == '{\n  "incognito": false,\n  "cleanup": true,\n  "sounds": true,\n  "hotkey": {\n    "kind": "fn",\n    "keycode": 63,\n    "label": "fn"\n  },\n  "onboarded": false\n}'

    def test_saved_file_is_readable_json(self):
        settings.save(settings.Settings(incognito=True))
        assert json.loads(settings.SETTINGS_PATH.read_text()) == {"incognito": True, "cleanup": True, "sounds": True, "hotkey": {"kind": "fn", "keycode": 63, "label": "fn"}, "onboarded": False}

    def test_partial_file_fills_defaults(self):
        settings.SETTINGS_PATH.parent.mkdir(parents=True)
        settings.SETTINGS_PATH.write_text('{"incognito": true}')
        s = settings.load()
        assert s.incognito is True and s.cleanup is True

    def test_unknown_keys_ignored(self):
        settings.SETTINGS_PATH.parent.mkdir(parents=True)
        settings.SETTINGS_PATH.write_text('{"cleanup": false, "from_the_future": 42}')
        assert settings.load().cleanup is False

    @pytest.mark.parametrize("content", ["not json", "{", ""])
    def test_corrupt_file_falls_back_to_defaults(self, content, capsys):
        settings.SETTINGS_PATH.parent.mkdir(parents=True)
        settings.SETTINGS_PATH.write_text(content)
        assert settings.load() == settings.Settings()
        assert "ignoring unreadable settings" in capsys.readouterr().err


# --- models --------------------------------------------------------------------------

PAYLOAD = b"model-bytes-" * 100_000  # ~1.2 MB, several download chunks


def spec_for(data=PAYLOAD, **kw):
    return ModelSpec(kw.pop("filename", "test.bin"), kw.pop("size", len(data)),
                     kw.pop("sha256", hashlib.sha256(data).hexdigest()), **kw)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


@pytest.fixture
def serve(monkeypatch):
    """Serve bytes to urllib.urlopen; records requested URLs."""
    requested = []

    def install(data=PAYLOAD):
        def urlopen(url, timeout=None):
            requested.append(url)
            return FakeResponse(data)

        monkeypatch.setattr(models.urllib.request, "urlopen", urlopen)
        return requested

    return install


class TestModelSpec:
    def test_default_repo_is_whisper_cpp(self):
        assert spec_for().url == "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/test.bin"

    def test_custom_repo_url(self):
        assert spec_for(repo="org/name").url == "https://huggingface.co/org/name/resolve/main/test.bin"

    def test_path_is_in_models_dir(self):
        assert spec_for().path == models.MODELS_DIR / "test.bin"

    @pytest.mark.parametrize("spec", [models.WHISPER_TURBO_Q5, models.GEMMA3_4B_Q4])
    def test_shipped_specs_are_well_formed(self, spec):
        assert re.fullmatch(r"[0-9a-f]{64}", spec.sha256)
        assert spec.size > 100_000_000
        assert spec.url.startswith("https://huggingface.co/") and spec.url.endswith(spec.filename)

    def test_spec_is_immutable(self):
        import dataclasses
        with pytest.raises(dataclasses.FrozenInstanceError):
            spec_for().size = 1

    def test_configured_models(self):
        assert models.DEFAULT_MODEL is models.WHISPER_TURBO_Q5
        assert models.CLEANUP_MODEL is models.GEMMA3_4B_Q4


class TestIsInstalled:
    def test_missing(self):
        assert not models.is_installed(spec_for())

    def test_wrong_size(self):
        s = spec_for()
        s.path.parent.mkdir(parents=True)
        s.path.write_bytes(PAYLOAD[:-1])
        assert not models.is_installed(s)

    def test_correct_size(self):
        s = spec_for()
        s.path.parent.mkdir(parents=True)
        s.path.write_bytes(PAYLOAD)
        assert models.is_installed(s)


class TestEnsureModel:
    def test_downloads_verifies_and_installs(self, serve):
        requested = serve()
        s = spec_for()
        assert models.ensure_model(s) == s.path
        assert s.path.read_bytes() == PAYLOAD
        assert requested == [s.url]

    def test_creates_missing_models_folder_tree(self, serve, monkeypatch, tmp_path):
        monkeypatch.setattr(models, "MODELS_DIR", tmp_path / "x" / "y" / "models")
        serve()
        assert models.ensure_model(spec_for()).exists()

    def test_download_has_a_timeout(self, monkeypatch):
        seen = {}

        def urlopen(url, timeout=None):
            seen["timeout"] = timeout
            return FakeResponse(PAYLOAD)

        monkeypatch.setattr(models.urllib.request, "urlopen", urlopen)
        models.ensure_model(spec_for())
        assert seen["timeout"] and 0 < seen["timeout"] <= 60

    def test_no_partial_file_left_after_success(self, serve):
        serve()
        s = spec_for()
        models.ensure_model(s)
        assert not list(s.path.parent.glob("*.part"))

    def test_progress_reports_monotonic_to_total(self, serve):
        serve()
        seen = []
        models.ensure_model(spec_for(), progress=lambda done, total: seen.append((done, total)))
        dones = [d for d, _ in seen]
        assert len(seen) > 1 and dones == sorted(dones)
        assert seen[-1] == (len(PAYLOAD), len(PAYLOAD))

    def test_already_installed_skips_download(self, serve):
        requested = serve()
        s = spec_for()
        s.path.parent.mkdir(parents=True)
        s.path.write_bytes(PAYLOAD)
        assert models.ensure_model(s) == s.path and requested == []

    def test_checksum_mismatch_rejected_and_cleaned_up(self, serve):
        serve()
        s = spec_for(sha256="0" * 64)
        with pytest.raises(RuntimeError, match="verification"):
            models.ensure_model(s)
        assert not s.path.exists() and not list(s.path.parent.glob("*.part"))

    def test_truncated_download_rejected(self, serve):
        serve(PAYLOAD[:1000])
        s = spec_for()
        with pytest.raises(RuntimeError):
            models.ensure_model(s)
        assert not s.path.exists()

    def test_network_error_propagates(self, monkeypatch):
        def urlopen(url, timeout=None):
            raise OSError("offline")

        monkeypatch.setattr(models.urllib.request, "urlopen", urlopen)
        with pytest.raises(OSError):
            models.ensure_model(spec_for())

    def test_corrupt_existing_file_is_replaced(self, serve):
        serve()
        s = spec_for()
        s.path.parent.mkdir(parents=True)
        s.path.write_bytes(b"old junk")
        models.ensure_model(s)
        assert s.path.read_bytes() == PAYLOAD


# --- setup ---------------------------------------------------------------------------
# Small fake specs are injected (install_async(specs=...)), so progress fractions are exact.

A = ModelSpec("a.bin", 300, "0" * 64)
B = ModelSpec("b.bin", 100, "0" * 64)


def run_install(monkeypatch, ensure, specs=(A, B)):
    monkeypatch.setattr(setup, "ensure_model", ensure)
    got = {"progress": [], "done": 0, "errors": []}
    setup.install_async(got["progress"].append, lambda: got.__setitem__("done", got["done"] + 1),
                        got["errors"].append, specs=specs)
    return got


def fake_download(downloaded):
    def ensure(spec, progress):
        progress(spec.size // 2, spec.size)
        progress(spec.size, spec.size)
        downloaded.append(spec)
    return ensure


class TestSetup:
    def test_required_models(self):
        assert setup.REQUIRED == (models.DEFAULT_MODEL, models.CLEANUP_MODEL)

    def test_missing_defaults_to_required(self):
        assert setup.missing() == list(setup.REQUIRED)  # nothing installed in the tmp models dir

    def test_missing_excludes_installed(self, monkeypatch):
        monkeypatch.setattr(setup, "is_installed", lambda s: s is A)
        assert setup.missing([A, B]) == [B]

    def test_nothing_missing(self, monkeypatch):
        monkeypatch.setattr(setup, "is_installed", lambda s: True)
        assert setup.missing([A, B]) == []

    def test_progress_is_exact_fraction_of_all_bytes(self, monkeypatch):
        downloaded = []
        got = run_install(monkeypatch, fake_download(downloaded))
        # A: 150/400, 300/400; then B continues from 300: 350/400, 400/400
        assert got["progress"] == [0.375, 0.75, 0.875, 1.0]
        assert downloaded == [A, B] and got["done"] == 1 and got["errors"] == []

    def test_install_only_downloads_missing(self, monkeypatch):
        monkeypatch.setattr(setup, "is_installed", lambda s: s is A)
        downloaded = []
        got = run_install(monkeypatch, fake_download(downloaded))
        assert downloaded == [B] and got["progress"] == [0.5, 1.0]

    def test_runs_on_named_daemon_worker(self, monkeypatch, inline_threads):
        run_install(monkeypatch, fake_download([]))
        assert inline_threads == ["model-setup"]

    def test_install_failure_reports_error(self, monkeypatch):
        def ensure(spec, progress):
            raise RuntimeError("model download failed verification")

        got = run_install(monkeypatch, ensure)
        assert got["errors"] == ["model download failed verification"] and got["done"] == 0

    def test_install_stops_after_first_failure(self, monkeypatch):
        attempts = []

        def ensure(spec, progress):
            attempts.append(spec)
            raise OSError("offline")

        run_install(monkeypatch, ensure)
        assert attempts == [A]

    def test_install_with_nothing_missing_finishes(self, monkeypatch):
        monkeypatch.setattr(setup, "is_installed", lambda s: True)
        got = run_install(monkeypatch, lambda spec, progress: pytest.fail("should not download"))
        assert got["done"] == 1 and got["progress"] == []

    def test_defaults_install_the_required_models(self, monkeypatch):
        downloaded = []
        monkeypatch.setattr(setup, "ensure_model", lambda spec, progress: downloaded.append(spec))
        setup.install_async(lambda f: None, lambda: None, lambda e: None)
        assert downloaded == list(setup.REQUIRED)


# --- levels ---------------------------------------------------------------------------

class TestFakeLevels:
    def test_always_in_range(self):
        src = levels.FakeLevelSource()
        values = [src.level(t / 100) for t in range(5000)]
        assert all(0.0 <= v <= 1.0 for v in values)

    def test_varies_over_time(self):
        src = levels.FakeLevelSource()
        values = {round(src.level(t / 10), 3) for t in range(200)}
        assert len(values) > 50

    def test_has_quiet_and_loud_moments(self):
        src = levels.FakeLevelSource()
        values = [src.level(t / 50) for t in range(3000)]
        assert min(values) < 0.2 and max(values) > 0.6

    def test_instances_are_offset(self):
        a, b = levels.FakeLevelSource(), levels.FakeLevelSource()
        assert a._offset != b._offset

    def test_seeded_sequence_matches_snapshot(self, golden_json):
        """Characterization test: pins the exact synthetic waveform for a fixed seed."""
        import random
        random.seed(1234)
        src = levels.FakeLevelSource()
        golden_json("fake_levels_seed1234", {
            "offset": round(src._offset, 9),
            "levels": [round(src.level(t / 20), 9) for t in range(120)],
        })
