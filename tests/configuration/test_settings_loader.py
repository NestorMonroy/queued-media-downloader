from pathlib import Path

import pytest

from queued_media_downloader.configuration import (
    SettingsError,
    load_settings,
    project_root,
)

ENVIRONMENT_PREFIX = "QUEUED_MEDIA_DOWNLOADER_"


def write_config(tmp_path: Path, content: str) -> Path:
    config_file = tmp_path / "config.toml"
    config_file.write_text(content, encoding="utf-8")
    return config_file


def test_defaults_apply_when_no_source_sets_a_value(tmp_path: Path) -> None:
    settings = load_settings(
        command_line_values={},
        environment={},
        config_file=tmp_path / "missing.toml",
    )

    assert settings.download_directory == (
        Path.home() / "Downloads" / "queued-media-downloader"
    )
    assert settings.state_directory == project_root() / "state"
    assert settings.worker_count == 1
    assert settings.progress_interval_seconds == 0.5
    assert settings.default_format_selector == "bv*+ba/b"
    assert settings.single_media_output_template == "%(title)s [%(id)s].%(ext)s"
    assert settings.max_filename_length == 150
    assert settings.ffmpeg_path is None


def test_config_file_overrides_defaults(tmp_path: Path) -> None:
    config_file = write_config(tmp_path, "worker_count = 2\n")

    settings = load_settings(
        command_line_values={}, environment={}, config_file=config_file
    )

    assert settings.worker_count == 2


def test_environment_overrides_config_file(tmp_path: Path) -> None:
    config_file = write_config(tmp_path, "worker_count = 2\n")

    settings = load_settings(
        command_line_values={},
        environment={f"{ENVIRONMENT_PREFIX}WORKER_COUNT": "3"},
        config_file=config_file,
    )

    assert settings.worker_count == 3


def test_command_line_overrides_environment(tmp_path: Path) -> None:
    config_file = write_config(tmp_path, "worker_count = 2\n")

    settings = load_settings(
        command_line_values={"worker_count": 4},
        environment={f"{ENVIRONMENT_PREFIX}WORKER_COUNT": "3"},
        config_file=config_file,
    )

    assert settings.worker_count == 4


def test_command_line_value_none_means_not_given(tmp_path: Path) -> None:
    settings = load_settings(
        command_line_values={"worker_count": None},
        environment={f"{ENVIRONMENT_PREFIX}WORKER_COUNT": "3"},
        config_file=tmp_path / "missing.toml",
    )

    assert settings.worker_count == 3


def test_text_values_are_converted_to_each_setting_type(tmp_path: Path) -> None:
    settings = load_settings(
        command_line_values={},
        environment={
            f"{ENVIRONMENT_PREFIX}PROGRESS_INTERVAL_SECONDS": "0.25",
            f"{ENVIRONMENT_PREFIX}FFMPEG_PATH": "C:/tools/ffmpeg",
            f"{ENVIRONMENT_PREFIX}DOWNLOAD_DIRECTORY": "D:/media",
        },
        config_file=tmp_path / "missing.toml",
    )

    assert settings.progress_interval_seconds == 0.25
    assert settings.ffmpeg_path == Path("C:/tools/ffmpeg")
    assert settings.download_directory == Path("D:/media")


def test_variables_without_the_prefix_are_ignored(tmp_path: Path) -> None:
    settings = load_settings(
        command_line_values={},
        environment={"WORKER_COUNT": "9", "PATH": "/usr/bin"},
        config_file=tmp_path / "missing.toml",
    )

    assert settings.worker_count == 1


@pytest.mark.parametrize(
    ("config_content", "named_key"),
    [
        ("worker_count = 0\n", "worker_count"),
        ('worker_count = "two"\n', "worker_count"),
        ("progress_interval_seconds = -1\n", "progress_interval_seconds"),
        ('default_format_selector = ""\n', "default_format_selector"),
        ("worker_cuont = 2\n", "worker_cuont"),
    ],
    ids=[
        "zero workers",
        "workers not a number",
        "negative interval",
        "empty format selector",
        "unknown key",
    ],
)
def test_invalid_setting_raises_an_error_naming_the_key(
    tmp_path: Path, config_content: str, named_key: str
) -> None:
    config_file = write_config(tmp_path, config_content)

    with pytest.raises(SettingsError, match=named_key):
        load_settings(command_line_values={}, environment={}, config_file=config_file)


def test_unknown_prefixed_environment_variable_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SettingsError, match="WORKER_CUONT"):
        load_settings(
            command_line_values={},
            environment={f"{ENVIRONMENT_PREFIX}WORKER_CUONT": "2"},
            config_file=tmp_path / "missing.toml",
        )


def test_malformed_config_file_raises_an_error_naming_the_file(
    tmp_path: Path,
) -> None:
    config_file = write_config(tmp_path, "worker_count = = 2\n")

    with pytest.raises(SettingsError, match=r"config\.toml"):
        load_settings(command_line_values={}, environment={}, config_file=config_file)


def test_project_root_contains_the_project_configuration() -> None:
    assert (project_root() / "pyproject.toml").is_file()
