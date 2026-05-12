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
        "Returns the structure of a prior state without its content — "
        "field names, types, sizes, and a token estimate. Cheap "
        "introspection: decide what's worth retrieving before "
        "retrieving it. Address by cycle (in-session) or record_id "
        "(cross-session UUID)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cycle": {
                "type": "integer",
                "description": "The cycle number to inspect (in-session).",
            },
            "record_id": {
                "type": "string",
                "description": (
                    "UUID of a record (cross-session). Obtain via recall, "
                    "search_memory, or walk results that carry record_id."
                ),
            },
            "reason": _REASON_FIELD,
        },
        "required": [],
    },
}

RECALL_SCHEMA = {
    "name": "recall",
    "description": (
        "Retrieve content from a prior state. Five mutually exclusive "
        "modes: (a) cycle + field: one field at one cycle (session-scoped); "
        "(b) cycle alone: the full state snapshot (session-scoped); "
        "(c) recent + field: the last N values of one field across states; "
        "(d) random + field: one value of the field from a randomly chosen "
        "state; (e) record_id: address a specific record by UUID "
        "(cross-session). What you retrieve is what you claimed then, not "
        "necessarily what was true."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cycle": {
                "type": "integer",
                "description": "Which cycle to recall (in-session only).",
            },
            "record_id": {
                "type": "string",
                "description": (
                    "UUID of a specific record (cross-session by construction)."
                ),
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
                    "If true, pick a random prior state containing `field`."
                ),
            },
            "scope": {
                "type": "string",
                "enum": ["session", "cross_session", "all"],
                "description": (
                    "Which states are eligible for recent/random: 'session' "
                    "(default, this session only), 'cross_session' (other "
                    "sessions only), 'all' (union). cycle and record_id "
                    "ignore scope."
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
        "Traverse the composition graph from a starting point. Two "
        "addressing modes: from_cycle walks in-session cycle-adjacency; "
        "from_record_id follows composition edges across sessions. "
        "direction chooses forward, backward, or both. depth controls "
        "how many steps. Each step returns record_id, field names, and "
        "a short summary — not full content. Use recall afterward if a "
        "step looks worth loading."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "from_cycle": {
                "type": "integer",
                "description": "The cycle to walk from (in-session).",
            },
            "from_record_id": {
                "type": "string",
                "description": (
                    "UUID to walk from (cross-session, via composition edges)."
                ),
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
        "required": [],
    },
}

SEARCH_MEMORY_SCHEMA = {
    "name": "search_memory",
    "description": (
        "Keyword/substring search across prior states. Structural "
        "narrowing happens first: cycle_range restricts to a span "
        "(in-session only), has_field requires a named field's presence, "
        "fields restricts the match scope to listed field names. Then "
        "the query is matched case-insensitively against the narrowed "
        "candidates. In-session results come first (cycle descending); "
        "cross-session results follow and carry record_id + session in "
        "place of cycle."
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
                        "description": (
                            "[lo, hi] inclusive cycle range (in-session only)."
                        ),
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
            "scope": {
                "type": "string",
                "enum": ["session", "cross_session", "all"],
                "description": (
                    "'session' (default, this session only), 'cross_session' "
                    "(hamutay-tagged records from other sessions), 'all' "
                    "(union, in-session first)."
                ),
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


from hamutay.tools.graph import RELATION_TYPE_NAMES


STORE_SCHEMA = {
    "name": "store",
    "description": (
        "Write a typed record into the open-records collection. The "
        "record carries the current session's provenance (you can't forge "
        "authorship) and the 'instance_authored' lineage tag so it's "
        "distinguishable from cycle-state records. Returns the record_id "
        "— hold it if you want to reference the record later (annotate_edge, "
        "recall, memory_schema)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "object",
                "description": (
                    "The payload to store. Fields are free-form; shape "
                    "is yours to choose."
                ),
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Additional lineage tags. Appended to the framework "
                    "defaults ('hamutay', 'instance_authored', 'cycle-N')."
                ),
            },
            "reason": _REASON_FIELD,
        },
        "required": ["content"],
    },
}

ANNOTATE_EDGE_SCHEMA = {
    "name": "annotate_edge",
    "description": (
        "Author a composition edge between two records. Lets you assert a "
        "structural relationship the framework didn't — a hypothesis "
        "CONFIRMS a prior observation, a revision CORRECTS an earlier "
        "claim, a tangent BRANCHES_FROM a main thread. Edges become "
        "traversable by walk(from_record_id)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "from_record_id": {
                "type": "string",
                "description": "UUID of the edge's origin record.",
            },
            "to_record_id": {
                "type": "string",
                "description": "UUID of the edge's target record.",
            },
            "relation": {
                "type": "string",
                "enum": list(RELATION_TYPE_NAMES),
                "description": (
                    "Relation type. One of the existing RelationType "
                    "enum values."
                ),
            },
            "reason": _REASON_FIELD,
        },
        "required": ["from_record_id", "to_record_id", "relation"],
    },
}


BASH_SCHEMA = {
    "name": "bash",
    "description": (
        "Execute a bash command. Returns stdout, stderr, and exit_code. "
        "Working directory is the project root. Bash is unscoped — it "
        "can reach anywhere the running process can, including outside "
        "the project. The framework does not gate which commands you "
        "run; the discipline lives in your voice. The soft norm is to "
        "flag irreversible-or-shared-state actions in conversation "
        "before executing them. Output past a per-stream cap is "
        "truncated in-band; timeout defaults to 60s, max 600s."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": (
                    "Timeout in seconds. Default 60, max 600. "
                    "Long-running commands should raise this deliberately "
                    "rather than relying on the default."
                ),
            },
            "reason": _REASON_FIELD,
        },
        "required": ["command"],
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
    "store": STORE_SCHEMA,
    "annotate_edge": ANNOTATE_EDGE_SCHEMA,
    "bash": BASH_SCHEMA,
}
