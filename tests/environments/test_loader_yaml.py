import os
from pathlib import Path

import pytest
import yaml

from lilya.environments import EnvironLoader
from lilya.exceptions import EnvError


@pytest.fixture()
def tmp_env_files(tmp_path: Path):
    """Creates temporary YAML and .env files for testing."""
    env_file = tmp_path / ".env"
    yaml_file = tmp_path / "config.yaml"

    env_file.write_text(
        """# Test environment
PROJECT_NAME=project-x
API_URL=https://api.example.com
PASSWORD=secret
EMPTY=
"""
    )

    yaml_file.write_text(
        yaml.safe_dump(
            {
                "project": {
                    "name": "${PROJECT_NAME|default-project}",
                    "description": "A test project",
                },
                "service": {
                    "host": "localhost",
                    "port": 8000,
                    "url": "${API_URL}",
                    "enabled": "${ENABLED|false}",
                },
                "nested": {
                    "values": {
                        "a": 1,
                        "b": 2,
                        "c": "${MISSING_VAR|fallback}",
                    }
                },
                "list_example": ["${PROJECT_NAME}", "item2", "item3"],
            }
        )
    )

    return yaml_file, env_file


def test_loads_env_and_yaml(tmp_env_files):
    yaml_file, env_file = tmp_env_files
    loader = EnvironLoader(env_file=env_file)

    loader.load_from_files(env_file=env_file, yaml_file=yaml_file)

    assert loader["PROJECT_NAME"] == "project-x"
    assert loader["API_URL"] == "https://api.example.com"
    assert loader["PASSWORD"] == "secret"

    # Flattened YAML values
    assert loader["project.name"] == "project-x"
    assert loader["service.port"] == "8000"
    assert loader["nested.values.c"] == "fallback"
    assert loader["list_example.0"] == "project-x"


def test_expands_env_defaults_and_system_vars(tmp_env_files, monkeypatch):
    yaml_file, env_file = tmp_env_files
    monkeypatch.setenv("ENABLED", "true")

    loader = EnvironLoader(env_file=env_file)
    loader.load_from_files(env_file=env_file, yaml_file=yaml_file)

    assert loader["service.enabled"].lower() == "true"
    assert loader["nested.values.c"] == "fallback"


def test_handles_missing_files_gracefully(tmp_path):
    env_file = tmp_path / "nonexistent.env"
    yaml_file = tmp_path / "nonexistent.yaml"

    with pytest.warns(UserWarning):
        loader = EnvironLoader(env_file=env_file)
    with pytest.warns(UserWarning):
        loader.load_from_files(env_file=str(env_file), yaml_file=str(yaml_file))
    assert isinstance(loader, EnvironLoader)
    assert len(loader) == len(os.environ)


def test_duplicate_variables_raise_error(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        """PROJECT=one
PROJECT=two
"""
    )
    loader = EnvironLoader()
    with pytest.raises(EnvError):
        loader._read_env_file(env_file, strict=True)


def test_duplicate_variables_warn_when_not_strict(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        """PROJECT=one
PROJECT=two
"""
    )
    loader = EnvironLoader()
    # Should not raise if strict=False
    with pytest.warns(UserWarning):
        loader._read_env_file(env_file, strict=False)


def test_yaml_expansion_with_env(tmp_path, monkeypatch):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        """
project:
  name: "${PROJECT_NAME|default}"
  code: "${CODE|999}"
  mix: "ID-${CODE|999}-NAME-${PROJECT_NAME|default}"
"""
    )

    monkeypatch.setenv("PROJECT_NAME", "demo")
    monkeypatch.setenv("CODE", "123")

    loader = EnvironLoader()
    data = loader._read_yaml_file(yaml_file)

    assert data["project"]["name"] == "demo"
    assert data["project"]["code"] == "123"
    assert data["project"]["mix"] == "ID-123-NAME-demo"


def test_flattened_keys():
    loader = EnvironLoader()
    data = {"a": {"b": {"c": 1}}, "x": 2}
    flattened = loader._flatten_dict(data)
    assert flattened == {"a.b.c": 1, "x": 2}


def test_load_from_files_merges_os_env(tmp_env_files, monkeypatch):
    yaml_file, env_file = tmp_env_files
    monkeypatch.setenv("EXTRA", "YES")

    loader = EnvironLoader()
    loader.load_from_files(env_file=env_file, yaml_file=yaml_file, include_os_env=True)

    assert loader["EXTRA"] == "YES"
    assert loader["project.name"] == "project-x"


def test_boolean_casting_and_defaults(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("FLAG=true\nFLAG2=0\nFLAG3=no\n")

    loader = EnvironLoader(env_file=env_file)
    loader.load_from_files(env_file=env_file)

    assert loader("FLAG", cast=bool) is True
    assert loader("FLAG2", cast=bool) is False
    assert loader("FLAG3", cast=bool) is False
    assert loader("MISSING_FLAG", cast=bool, default=True) is True


def test_contains_and_get_with_defaults(tmp_env_files):
    yaml_file, env_file = tmp_env_files
    loader = EnvironLoader(env_file=env_file)
    loader.load_from_files(env_file=env_file, yaml_file=yaml_file)

    assert "PROJECT_NAME" in loader
    assert "NON_EXISTENT" not in loader
    assert loader.get("PROJECT_NAME") == "project-x"
    assert loader.get("NON_EXISTENT", default="default") == "default"


def test_export_and_keys(tmp_env_files):
    yaml_file, env_file = tmp_env_files
    loader = EnvironLoader(env_file=env_file)
    loader.load_from_files(env_file=env_file, yaml_file=yaml_file)

    exported = loader.export()
    keys = list(loader.keys())

    # Keys should be in exported dictionary
    for key in keys:
        assert key in exported
    # Exported keys should match keys()
    assert set(exported.keys()) == set(keys)


def test_strict_missing_variable_raises(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING=val\n")
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        """
value: "${MISSING_VAR}"
"""
    )

    loader = EnvironLoader(env_file=env_file)
    with pytest.raises(EnvError):
        loader.load_from_files(env_file=env_file, yaml_file=yaml_file, strict=True)


def test_escaped_dollar_variables(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        """
value1: "$${NOT_A_VAR}"
value2: "Price is $$5"
"""
    )
    loader = EnvironLoader()
    data = loader._read_yaml_file(yaml_file)

    assert data["value1"] == "${NOT_A_VAR}" or data["value1"] == "$${NOT_A_VAR}"
    assert data["value2"] == "Price is $5" or data["value2"] == "Price is $$5"


def test_flatten_disabled(tmp_env_files):
    yaml_file, env_file = tmp_env_files
    loader = EnvironLoader(env_file=env_file)
    loader.load_from_files(env_file=env_file, yaml_file=yaml_file, flatten=False)

    # The nested dicts should remain nested
    assert isinstance(loader["project"], dict)
    assert isinstance(loader["nested"]["values"], dict)
    # Check that flattened keys are not present
    assert "project.name" not in loader


def test_home_expansion_in_yaml(tmp_path, monkeypatch):
    yaml_file = tmp_path / "config.yaml"
    home = os.path.expanduser("~")
    yaml_file.write_text(
        """
path: "${HOME}/folder"
"""
    )
    monkeypatch.setenv("HOME", home)
    loader = EnvironLoader()
    data = loader._read_yaml_file(yaml_file)
    assert data["path"] == f"{home}/folder"


def test_unicode_environment_variables(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ÜSER=välue\n")
    loader = EnvironLoader(env_file=env_file)
    loader.load_from_files(env_file=env_file)
    assert loader["ÜSER"] == "välue"


def test_override_with_kwargs(tmp_env_files):
    yaml_file, env_file = tmp_env_files
    loader = EnvironLoader(env_file=env_file)
    loader.load_from_files(
        env_file=env_file, yaml_file=yaml_file, overrides={"PROJECT_NAME": "override"}
    )
    assert loader["PROJECT_NAME"] == "override"
    # Also check that YAML expansion uses the overridden value
    assert loader["project.name"] == "override"


def test_complex_nested_yaml_expansion(tmp_path, monkeypatch):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        """
nested:
  list:
    - "${VAR1|default1}"
    - "${VAR2|default2}"
  dict:
    key1: "${VAR3|default3}"
    key2: "${VAR4|default4}"
"""
    )
    monkeypatch.setenv("VAR1", "value1")
    monkeypatch.setenv("VAR4", "value4")

    loader = EnvironLoader()
    data = loader._read_yaml_file(yaml_file)

    assert data["nested"]["list"][0] == "value1"
    assert data["nested"]["list"][1] == "default2"
    assert data["nested"]["dict"]["key1"] == "default3"
    assert data["nested"]["dict"]["key2"] == "value4"
