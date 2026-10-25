"""Single-request stdlib HTTP worker. Source data arrives only on bounded stdin."""

import sys

from aegis.adapters.local_llm import (
    LocalLLMError, LocalLLMProvider, MAX_REQUEST_BYTES, MAX_WORKER_BYTES,
    WORKER_ERROR_CODES, _decode_json, _encode_json,
)


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise LocalLLMError("input_too_large")
        packet = _decode_json(raw, code="invalid_request")
        if (not isinstance(packet, dict)
                or set(packet) != {"protocol", "host", "model", "timeout", "path", "body"}
                or type(packet["protocol"]) is not int or packet["protocol"] != 1):
            raise LocalLLMError("invalid_request")
        provider = LocalLLMProvider(host=packet["host"], model=packet["model"], timeout=packet["timeout"])
        result = provider._http_json(packet["path"], packet["body"])
        output = _encode_json({"ok": True, "result": result}, code="invalid_response")
        if len(output) > MAX_WORKER_BYTES:
            raise LocalLLMError("response_too_large")
    except LocalLLMError as error:
        code = error.code if error.code in WORKER_ERROR_CODES else "service_error"
        output = _encode_json({"ok": False, "error": code})
    except Exception:
        # Neither source text, server content, paths nor exception messages leave
        # this process through a diagnostic traceback or an error envelope.
        output = _encode_json({"ok": False, "error": "service_error"})
    sys.stdout.buffer.write(output)
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
