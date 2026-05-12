"""Compatibility harness for taste_open tool-calling profiles.

Writes a capability registry JSON keyed by "provider:model".
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict

from hamutay.taste_open import CapabilityProfile, OpenAITasteBackend


def _probe_once(
    provider: str,
    model: str,
    base_url: str,
    api_key: str,
    require_parameters: bool,
    provider_order: list[str],
    only_providers: list[str],
    tool_choice_mode: str,
    parallel_tool_calls: bool,
) -> tuple[bool, str]:
    profile = CapabilityProfile(
        supports_tools=True,
        supports_parallel_tool_calls=parallel_tool_calls,
        tool_choice_mode=tool_choice_mode,
        prefer_json_fallback=False,
    )
    backend = OpenAITasteBackend(
        base_url=base_url,
        api_key=api_key,
        provider_name=provider,
        capability=profile,
        openrouter_require_parameters=require_parameters,
        openrouter_provider_order=provider_order,
        openrouter_only_providers=only_providers,
    )
    try:
        backend.call(
            model=model,
            system="Compatibility probe. Use think_and_respond with response='ok'.",
            messages=[{"role": "user", "content": "Probe."}],
            experiment_label="taste_open_compat",
        )
        return True, "tool_call_ok"
    except Exception as e:
        return False, str(e)


def _probe_modes(
    provider: str,
    model: str,
    base_url: str,
    api_key: str,
    require_parameters: bool,
    provider_order: list[str],
    only_providers: list[str],
) -> tuple[CapabilityProfile | None, list[str]]:
    attempts = [
        ("function_object", False),
        ("required", False),
        ("auto", False),
        ("auto", True),
    ]
    errors: list[str] = []
    for mode, parallel in attempts:
        ok, detail = _probe_once(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            require_parameters=require_parameters,
            provider_order=provider_order,
            only_providers=only_providers,
            tool_choice_mode=mode,
            parallel_tool_calls=parallel,
        )
        if ok:
            return (
                CapabilityProfile(
                    supports_tools=True,
                    supports_parallel_tool_calls=parallel,
                    tool_choice_mode=mode,
                    prefer_json_fallback=False,
                ),
                errors,
            )
        errors.append(
            f"require_parameters={require_parameters}, mode={mode}, "
            f"parallel={parallel}: {detail}"
        )
    return None, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe tool-call compatibility for taste_open")
    parser.add_argument("--provider", required=True, choices=["openrouter", "openai"])
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--out", required=True, help="Output JSON capability registry path")
    parser.add_argument("--openrouter-require-parameters", action="store_true")
    parser.add_argument("--openrouter-provider-order", default="")
    parser.add_argument("--openrouter-only-providers", default="")
    args = parser.parse_args()

    if args.provider == "openrouter":
        base_url = args.base_url or "https://openrouter.ai/api/v1"
        api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY", "")
    else:
        base_url = args.base_url or "https://api.openai.com/v1"
        api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")

    if not api_key:
        env_var = "OPENROUTER_API_KEY" if args.provider == "openrouter" else "OPENAI_API_KEY"
        raise SystemExit(f"No API key: pass --api-key or set {env_var}")

    provider_order = [p.strip() for p in args.openrouter_provider_order.split(",") if p.strip()]
    only_providers = [p.strip() for p in args.openrouter_only_providers.split(",") if p.strip()]

    selected: CapabilityProfile | None = None
    status = "no_supported_mode"
    errors: list[str] = []

    # Try strict route first if requested, then permissive route.
    strict_first = [True, False] if args.openrouter_require_parameters else [False, True]
    for req in strict_first:
        selected, probe_errors = _probe_modes(
            provider=args.provider,
            model=args.model,
            base_url=base_url,
            api_key=api_key,
            require_parameters=req,
            provider_order=provider_order,
            only_providers=only_providers,
        )
        errors.extend(probe_errors)
        if selected is not None:
            status = "tool_call_ok"
            break

    key = f"{args.provider}:{args.model}"
    registry = {}
    try:
        with open(args.out) as f:
            registry = json.load(f)
    except FileNotFoundError:
        pass

    if selected is None:
        selected = CapabilityProfile(supports_tools=False)

    record = asdict(selected)
    record["probe_status"] = status
    record["probe_errors"] = errors[-3:]
    registry[key] = record

    with open(args.out, "w") as f:
        json.dump(registry, f, indent=2)

    print(f"Wrote capability for {key}: {status}")
    if errors:
        print("Recent errors:")
        for err in errors[-3:]:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
