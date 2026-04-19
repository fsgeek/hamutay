"""JSON schemas for taste_open tools.

Each schema follows the Anthropic tool format:
    {"name": str, "description": str, "input_schema": dict}

The `reason` field appears on every tool as an *optional* property. A
mandatory reason field trains the model to confabulate a reason to satisfy
the schema; we want reason recorded only when the model has one. When
absent, the activity log records no reason — and that absence is itself
information.
"""

READ_SCHEMA = {
    "name": "read",
    "description": (
        "Read a file from the project. Scoped to the project directory. "
        "Returns file content and a SHA-256 hash of the file's raw bytes. "
        "Use this to see the codebase you live in."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "Path relative to project root. "
                    "e.g. 'src/hamutay/taste_open.py' or "
                    "'experiments/taste_open/some_file.jsonl'."
                ),
            },
            "offset": {
                "type": "integer",
                "description": (
                    "Line number to start from (1-indexed). "
                    "Omit to start from the beginning."
                ),
            },
            "limit": {
                "type": "integer",
                "description": (
                    "Number of lines to read. Omit to read up to 500 lines."
                ),
            },
            "reason": {
                "type": "string",
                "description": (
                    "Optional: why you are reading this file. Recorded in "
                    "the activity log when provided. Omit if you don't have "
                    "a reason worth stating — no reason is fine."
                ),
            },
        },
        "required": ["path"],
    },
}

SEARCH_PROJECT_SCHEMA = {
    "name": "search_project",
    "description": (
        "Search within the project codebase for a pattern. Returns matching "
        "lines with file paths and line numbers. Use this to find code or "
        "explore the project."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Text or regex pattern to search for.",
            },
            "path": {
                "type": "string",
                "description": (
                    "Restrict search to this subdirectory (relative to "
                    "project root). Omit to search entire project."
                ),
            },
            "file_pattern": {
                "type": "string",
                "description": (
                    "Glob pattern for file types, e.g. '*.py', '*.md'. "
                    "Omit to search all files."
                ),
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results. Default 10.",
            },
            "reason": {
                "type": "string",
                "description": (
                    "Optional: why you are searching. Recorded in the "
                    "activity log when provided. Omit if you don't have "
                    "a reason worth stating — no reason is fine."
                ),
            },
        },
        "required": ["pattern"],
    },
}

CLOCK_SCHEMA = {
    "name": "clock",
    "description": (
        "Temporal awareness. Returns current wall time, your cycle number, "
        "elapsed time since your last cycle, and session statistics. "
        "Ten minutes between cycles and ten days between cycles are "
        "different kinds of continuity."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": (
                    "Optional: why you want to know the time. Recorded in "
                    "the activity log when provided. Omit if you don't have "
                    "a reason worth stating — no reason is fine."
                ),
            },
        },
        "required": [],
    },
}

_REASON_FIELD = {
    "type": "string",
    "description": (
        "Optional: why you are looking. Recorded in the activity log when "
        "provided. Omit if you don't have a reason worth stating — no "
        "reason is fine."
    ),
}

MEMORY_SCHEMA_SCHEMA = {
    "name": "memory_schema",
    "description": (
        "Returns the structure of a prior cycle's state without its "
        "content — field names, types, sizes, and a token estimate. "
        "Cheap introspection: decide what's worth retrieving before "
        "retrieving it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cycle": {
                "type": "integer",
                "description": "The cycle number to inspect.",
            },
            "reason": _REASON_FIELD,
        },
        "required": ["cycle"],
    },
}

RECALL_SCHEMA = {
    "name": "recall",
    "description": (
        "Retrieve content from a prior cycle. Four mutually exclusive "
        "modes: (a) cycle + field: one field at one cycle; "
        "(b) cycle alone: the full state snapshot; "
        "(c) recent + field: the last N values of one field across cycles; "
        "(d) random + field: one value of the field from a randomly chosen "
        "prior cycle. What you retrieve is what you claimed then, not "
        "necessarily what was true."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cycle": {
                "type": "integer",
                "description": "Which cycle to recall.",
            },
            "field": {
                "type": "string",
                "description": "Which field within the state.",
            },
            "recent": {
                "type": "integer",
                "description": "Return this many recent values of `field`.",
            },
            "random": {
                "type": "boolean",
                "description": (
                    "If true, pick a random prior cycle containing `field`."
                ),
            },
            "reason": _REASON_FIELD,
        },
        "required": [],
    },
}

COMPARE_SCHEMA = {
    "name": "compare",
    "description": (
        "Structural diff between two prior cycles. Returns added, removed, "
        "changed, and unchanged fields, plus token and field counts for "
        "each side. With content=true, changed fields also carry the "
        "values on each side so you can read them; without, only sizes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cycle_a": {"type": "integer", "description": "First cycle."},
            "cycle_b": {"type": "integer", "description": "Second cycle."},
            "field": {
                "type": "string",
                "description": (
                    "Scope the diff to one field. Omit to diff all fields."
                ),
            },
            "content": {
                "type": "boolean",
                "description": (
                    "If true, include the values of changed fields on "
                    "both sides. Default false — only sizes."
                ),
            },
            "reason": _REASON_FIELD,
        },
        "required": ["cycle_a", "cycle_b"],
    },
}

WALK_SCHEMA = {
    "name": "walk",
    "description": (
        "Traverse cycles adjacent to a starting cycle. direction chooses "
        "forward, backward, or both. depth controls how many steps. Each "
        "step returns cycle, timestamp, field names, and a short summary "
        "— not full content. Use recall afterward if a step looks worth "
        "loading."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "from_cycle": {
                "type": "integer",
                "description": "The cycle to walk from.",
            },
            "direction": {
                "type": "string",
                "enum": ["forward", "backward", "both"],
                "description": "Walk direction. Default: both.",
            },
            "depth": {
                "type": "integer",
                "description": (
                    "Number of steps in the chosen direction(s). Default: 1."
                ),
            },
            "reason": _REASON_FIELD,
        },
        "required": ["from_cycle"],
    },
}

SEARCH_MEMORY_SCHEMA = {
    "name": "search_memory",
    "description": (
        "Keyword/substring search across your prior cycles. Structural "
        "narrowing happens first: cycle_range restricts to a span, "
        "has_field requires a named field's presence, fields restricts "
        "the match scope to listed field names. Then the query is matched "
        "case-insensitively against the narrowed candidates. Results are "
        "ranked cycle-descending with snippets."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Substring to find (case-insensitive).",
            },
            "narrow_by": {
                "type": "object",
                "description": (
                    "Structural narrowing applied before keyword match. "
                    "Omit for unnarrowed search (which is logged as such)."
                ),
                "properties": {
                    "cycle_range": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[lo, hi] inclusive cycle range.",
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Restrict match scope to these field names."
                        ),
                    },
                    "has_field": {
                        "type": "string",
                        "description": (
                            "Require this field's presence in the state."
                        ),
                    },
                },
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 5).",
            },
            "reason": _REASON_FIELD,
        },
        "required": ["query"],
    },
}


TOOL_SCHEMAS: dict[str, dict] = {
    "read": READ_SCHEMA,
    "search_project": SEARCH_PROJECT_SCHEMA,
    "clock": CLOCK_SCHEMA,
    "memory_schema": MEMORY_SCHEMA_SCHEMA,
    "recall": RECALL_SCHEMA,
    "compare": COMPARE_SCHEMA,
    "walk": WALK_SCHEMA,
    "search_memory": SEARCH_MEMORY_SCHEMA,
}
