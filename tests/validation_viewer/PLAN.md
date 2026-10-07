# Independent viewer validation plan

Authority: the contract in viewer/state.py, viewer/__main__.py, the page footer,
and the user's review request. Modify only this new validation package; leave
production code untouched; never run git. Known defects must fail normally,
without xfail or assertions that bless the current incorrect behavior.

1. Construct a temporary community with members, guests, valid plaza messages
   and delivery records, assembly records, event and billing logs, and private
   home files containing distinct secret sentinels (`conftest.py`).
2. Test gathering, metadata and billing, privacy (including forbidden reads),
   filesystem immutability, tolerant JSONL reads, plaza errors, and assembly
   extension rounds (`test_state.py`).
3. Exercise actual HTTP request dispatch using an in-memory connection, test
   the endpoint allowlist and unsupported writes, and intercept server startup
   to assert the sole bind address is 127.0.0.1 (`test_http.py`).
4. Execute page.html's actual script in Node's VM with a minimal document and
   disabled networking/timers. Inspect rendered HTML with Python's HTMLParser
   for injected elements/attributes, and pin public assembly/error content
   (`render_page.js`, `test_page.py`). This is script execution and HTML parsing,
   not a full browser integration test; Node must be available.
5. Run `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -p no:cacheprovider
   tests/validation_viewer -q` and report the actual failures with production
   file:line references. Add no production fixes and hide no failures.
