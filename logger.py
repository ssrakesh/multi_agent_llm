import json
import sys
import traceback

try:

    from pydantic import ValidationError as _ValidationError

except ImportError:

    class _ValidationError(Exception):

        """Unused placeholder when pydantic is absent."""

        pass


def _reconfigure_stdio_utf8():

    """Avoid UnicodeEncodeError on Windows cp1252 when logs include arrows, etc."""

    for name in ("stdout", "stderr"):

        stream = getattr(sys, name, None)

        if stream is None or not hasattr(stream, "reconfigure"):

            continue

        try:

            stream.reconfigure(encoding="utf-8", errors="replace")

        except (AttributeError, OSError, ValueError, TypeError):

            pass


_reconfigure_stdio_utf8()


def _emit(text: str) -> None:

    try:

        print(text)

    except UnicodeEncodeError:

        enc = getattr(sys.stdout, "encoding", None) or "ascii"

        try:

            safe = (
                text.encode(enc, errors="replace").decode(enc)
            )

        except LookupError:

            safe = (
                text.encode(
                    "ascii",
                    errors="replace",
                ).decode(
                    "ascii",
                )
            )

        print(safe)


def section(title):

    _emit("\n" + "=" * 70)

    _emit(title)

    _emit("=" * 70)


def sys_log(msg):

    _emit(f"[SYS] {msg}")


def proof_log(msg):

    _emit(f"[PROOF] {msg}")


def benchmark_log(msg):

    _emit(f"[BENCHMARK] {msg}")


def eval_log(msg):

    _emit(f"[EVAL] {msg}")


def pipeline_log(stage, msg):

    _emit(f"[PIPELINE::{stage}] {msg}")


def stage_log(stage, msg):

    _emit(f"[{stage}] {msg}")


def llm_log(msg):

    _emit(f"[LLM] {msg}")


def validate_log(msg):

    _emit(f"[VALIDATE] {msg}")


def react_log(role, msg):

    _emit(f"[REACT::{role}] {msg}")


def error_log(msg, exc=None, *, stack=None):

    """Log failures.

    Pass *exc* when Python raised — a traceback prints by default unless the
    exception is a handled model-output type (`JSONDecodeError` on LLM blobs,
    pydantic `ValidationError`) use *stack=False* at noisy call sites anyway.

    * *stack=None* — print traceback iff *exc* is set and type is neither
      `json.JSONDecodeError` nor `ValidationError`; pass *stack=True* for
      `JSONDecodeError` from reading project files (`inputs.json`, etc.).
    * *stack=True* — always print traceback when *exc* is set.
    * *stack=False* — never print traceback.

    Calls with ``exc=None`` are message-only (e.g. unparseable model text with
    no exception object).
    """

    if exc is None:

        _emit(f"[ERROR] {msg}")

        return

    q_modelish = isinstance(
        exc,
        (
            json.JSONDecodeError,
            _ValidationError,
        ),
    )

    if stack is False:

        want_tb = False

    elif stack is True:

        want_tb = True

    else:

        want_tb = not q_modelish

    line = f"[ERROR] {msg}: {exc}"

    if exc is not None and not want_tb and q_modelish:

        line += " (traceback suppressed: LLM/schema output — not treated as infra failure)"

    _emit(line)

    if want_tb:

        _emit(
            "".join(
                traceback.format_exception(
                    type(exc),
                    exc,
                    exc.__traceback__,
                ),
            ).rstrip("\n"),
        )
