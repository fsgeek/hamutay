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
        "lines with file paths and line numbers. Use this to find code, "
        "verify claims about what the code does, or explore the project."
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
                    "activity log when provided."
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
        "different kinds of continuity — check when it matters."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": (
                    "Optional: why you want to know the time. Recorded in "
                    "the activity log when provided."
                ),
            },
        },
        "required": [],
    },
}

TOOL_SCHEMAS: dict[str, dict] = {
    "read": READ_SCHEMA,
    "search_project": SEARCH_PROJECT_SCHEMA,
    "clock": CLOCK_SCHEMA,
}
