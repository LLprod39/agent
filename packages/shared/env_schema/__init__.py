"""Utilities for validating environment profile documents."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple

from ._simple_yaml import SimpleYAMLError, load as load_simple_yaml

SCHEMA_PATH = Path(__file__).resolve().parent / "environment-profile.schema.json"

_ALLOWED_TYPES = {"k8s", "vm", "docker", "bare-metal", "serverless"}
_ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
_ID_PATTERN = re.compile(r"^[a-z0-9-]+$")
_RUNBOOK_PATTERN = re.compile(r"^docs/runbooks/.+\.md$")


class ValidationError(Exception):
    """Raised when an environment profile does not match the expected shape."""

    def __init__(self, message: str, path: Tuple[str, ...] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.path = path or tuple()


def load_schema() -> Dict[str, Any]:
    """Return the environment profile JSON schema as a dict."""
    with SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_document(path: Path) -> Dict[str, Any]:
    """Load a YAML or JSON environment profile from *path*."""
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            data = load_simple_yaml(text)
        except SimpleYAMLError as exc:  # pragma: no cover - defensive
            raise ValidationError(f"Invalid YAML: {exc}") from exc
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValidationError(
            "Environment profile documents must decode into a mapping"
        )
    return data


def _raise(path: Tuple[str, ...], message: str) -> None:
    reference = ".".join(path)
    if reference:
        raise ValidationError(f"{reference}: {message}", path)
    raise ValidationError(message, path)


def _ensure_keys(
    mapping: Mapping[str, Any], required: Iterable[str], path: Tuple[str, ...]
) -> None:
    for key in required:
        if key not in mapping:
            _raise(path + (key,), "field is required")


def _ensure_allowed_keys(
    mapping: Mapping[str, Any], allowed: Iterable[str], path: Tuple[str, ...]
) -> None:
    allowed_set = set(allowed)
    for key in mapping.keys():
        if key not in allowed_set:
            _raise(path + (key,), "unexpected field")


def _ensure_type(value: Any, expected_type: type, path: Tuple[str, ...]) -> None:
    if not isinstance(value, expected_type):
        _raise(path, f"expected {expected_type.__name__}")


def _ensure_string(value: Any, path: Tuple[str, ...]) -> str:
    _ensure_type(value, str, path)
    return value


def validate_environment_profile(profile: Dict[str, Any]) -> None:
    """Raise :class:`ValidationError` if *profile* does not satisfy the schema."""
    if not isinstance(profile, dict):
        _raise((), "profile must be a mapping")

    required_keys = {"id", "type", "networking", "auth", "policies"}
    optional_keys = {
        "display_name",
        "description",
        "metadata",
        "cluster",
        "defaults",
        "runbooks",
        "notes",
        "ssh",
        "extensions",
    }
    _ensure_keys(profile, required_keys, ())
    _ensure_allowed_keys(profile, required_keys | optional_keys, ())

    profile_id = _ensure_string(profile["id"], ("id",))
    if not _ID_PATTERN.match(profile_id):
        _raise(("id",), "must be kebab-case (lowercase alphanumerics and dashes)")

    if "display_name" in profile:
        _ensure_string(profile["display_name"], ("display_name",))
    if "description" in profile:
        _ensure_string(profile["description"], ("description",))

    env_type = _ensure_string(profile["type"], ("type",))
    if env_type not in _ALLOWED_TYPES:
        _raise(("type",), f"must be one of {sorted(_ALLOWED_TYPES)}")

    if "metadata" in profile:
        metadata = profile["metadata"]
        _ensure_type(metadata, dict, ("metadata",))
        for meta_key, meta_value in metadata.items():
            if not isinstance(meta_key, str):
                _raise(("metadata",), "keys must be strings")
            if (
                not isinstance(meta_value, (str, int, float, bool))
                and meta_value is not None
            ):
                _raise(("metadata", meta_key), "values must be string/number/bool/null")

    if "ssh" in profile:
        ssh_cfg = profile["ssh"]
        _ensure_type(ssh_cfg, dict, ("ssh",))

        required_ssh_keys = {"host", "username"}
        optional_ssh_keys = {
            "port",
            "password",
            "private_key",
            "passphrase",
            "sudo_password",
            "become_user",
            "max_connection_attempts",
            "known_hosts",
            "jump_host",
            "labels",
        }

        _ensure_keys(ssh_cfg, required_ssh_keys, ("ssh",))
        _ensure_allowed_keys(ssh_cfg, required_ssh_keys | optional_ssh_keys, ("ssh",))

        _ensure_string(ssh_cfg["host"], ("ssh", "host"))
        _ensure_string(ssh_cfg["username"], ("ssh", "username"))

        if "port" in ssh_cfg:
            _ensure_type(ssh_cfg["port"], int, ("ssh", "port"))
            if not 1 <= ssh_cfg["port"] <= 65535:
                _raise(("ssh", "port"), "must be between 1 and 65535")

        for key in ("password", "private_key", "passphrase", "sudo_password", "become_user"):
            if key in ssh_cfg:
                _ensure_string(ssh_cfg[key], ("ssh", key))

        if "max_connection_attempts" in ssh_cfg:
            _ensure_type(
                ssh_cfg["max_connection_attempts"], int, ("ssh", "max_connection_attempts")
            )
            if ssh_cfg["max_connection_attempts"] < 1:
                _raise(("ssh", "max_connection_attempts"), "must be greater than zero")

        if "known_hosts" in ssh_cfg:
            _ensure_type(ssh_cfg["known_hosts"], list, ("ssh", "known_hosts"))
            for idx, value in enumerate(ssh_cfg["known_hosts"]):
                _ensure_string(value, ("ssh", "known_hosts", str(idx)))

        if "labels" in ssh_cfg:
            labels = ssh_cfg["labels"]
            _ensure_type(labels, dict, ("ssh", "labels"))
            for label_key, label_value in labels.items():
                if not isinstance(label_key, str):
                    _raise(("ssh", "labels"), "label keys must be strings")
                _ensure_string(label_value, ("ssh", "labels", label_key))

        if "jump_host" in ssh_cfg:
            jump_host = ssh_cfg["jump_host"]
            _ensure_type(jump_host, dict, ("ssh", "jump_host"))
            _ensure_keys(jump_host, {"host", "username"}, ("ssh", "jump_host"))
            _ensure_allowed_keys(
                jump_host,
                {"host", "username", "port", "password", "private_key", "passphrase"},
                ("ssh", "jump_host"),
            )
            _ensure_string(jump_host["host"], ("ssh", "jump_host", "host"))
            _ensure_string(jump_host["username"], ("ssh", "jump_host", "username"))
            if "port" in jump_host:
                _ensure_type(jump_host["port"], int, ("ssh", "jump_host", "port"))
                if not 1 <= jump_host["port"] <= 65535:
                    _raise(("ssh", "jump_host", "port"), "must be between 1 and 65535")
            for key in ("password", "private_key", "passphrase"):
                if key in jump_host:
                    _ensure_string(jump_host[key], ("ssh", "jump_host", key))

    if "cluster" in profile:
        cluster = profile["cluster"]
        _ensure_type(cluster, dict, ("cluster",))
        _ensure_keys(cluster, {"name"}, ("cluster",))
        _ensure_allowed_keys(cluster, {"name", "context", "namespace"}, ("cluster",))
        for key in cluster:
            _ensure_string(cluster[key], ("cluster", key))

    networking = profile["networking"]
    _ensure_type(networking, dict, ("networking",))
    _ensure_keys(networking, {"proxy"}, ("networking",))
    _ensure_allowed_keys(
        networking, {"proxy", "bastion", "allowed_endpoints"}, ("networking",)
    )

    proxy = networking["proxy"]
    _ensure_type(proxy, dict, ("networking", "proxy"))
    _ensure_allowed_keys(proxy, {"http", "https", "no_proxy"}, ("networking", "proxy"))
    for key in proxy:
        _ensure_string(proxy[key], ("networking", "proxy", key))

    if "bastion" in networking:
        _ensure_string(networking["bastion"], ("networking", "bastion"))
    if "allowed_endpoints" in networking:
        _ensure_type(
            networking["allowed_endpoints"], list, ("networking", "allowed_endpoints")
        )
        for idx, item in enumerate(networking["allowed_endpoints"]):
            _ensure_string(item, ("networking", "allowed_endpoints", str(idx)))

    auth = profile["auth"]
    _ensure_type(auth, dict, ("auth",))
    _ensure_allowed_keys(
        auth, {"vault_role", "ssh_cert_role", "service_account", "token_ref"}, ("auth",)
    )
    for key, value in auth.items():
        _ensure_string(value, ("auth", key))

    policies = profile["policies"]
    _ensure_type(policies, dict, ("policies",))
    _ensure_keys(policies, {"risk_level", "require_approval"}, ("policies",))
    _ensure_allowed_keys(
        policies,
        {"risk_level", "require_approval", "change_ticket_required"},
        ("policies",),
    )

    risk_level = _ensure_string(policies["risk_level"], ("policies", "risk_level"))
    if risk_level not in _ALLOWED_RISK_LEVELS:
        _raise(
            ("policies", "risk_level"), f"must be one of {sorted(_ALLOWED_RISK_LEVELS)}"
        )

    if not isinstance(policies["require_approval"], bool):
        _raise(("policies", "require_approval"), "must be boolean")
    if "change_ticket_required" in policies and not isinstance(
        policies["change_ticket_required"], bool
    ):
        _raise(("policies", "change_ticket_required"), "must be boolean")

    if "defaults" in profile:
        defaults = profile["defaults"]
        _ensure_type(defaults, dict, ("defaults",))
        _ensure_allowed_keys(
            defaults,
            {"namespace", "package_manager", "working_directory", "retries"},
            ("defaults",),
        )
        if "namespace" in defaults:
            _ensure_string(defaults["namespace"], ("defaults", "namespace"))
        if "package_manager" in defaults:
            _ensure_string(defaults["package_manager"], ("defaults", "package_manager"))
        if "working_directory" in defaults:
            _ensure_string(
                defaults["working_directory"], ("defaults", "working_directory")
            )
        if "retries" in defaults:
            if not isinstance(defaults["retries"], int) or defaults["retries"] < 0:
                _raise(("defaults", "retries"), "must be a non-negative integer")

    if "runbooks" in profile:
        runbooks = profile["runbooks"]
        _ensure_type(runbooks, list, ("runbooks",))
        for idx, entry in enumerate(runbooks):
            path = _ensure_string(entry, ("runbooks", str(idx)))
            if not _RUNBOOK_PATTERN.match(path):
                _raise(("runbooks", str(idx)), "must reference docs/runbooks/*.md")

    if "notes" in profile:
        _ensure_string(profile["notes"], ("notes",))

    if "extensions" in profile:
        _ensure_type(profile["extensions"], dict, ("extensions",))


def validate_environment_profile_file(path: str | Path) -> Dict[str, Any]:
    """Validate the document at *path* and return its dictionary form."""
    resolved = Path(path).resolve()
    profile = _load_document(resolved)
    validate_environment_profile(profile)
    return profile


__all__ = [
    "SCHEMA_PATH",
    "ValidationError",
    "load_schema",
    "validate_environment_profile",
    "validate_environment_profile_file",
]
