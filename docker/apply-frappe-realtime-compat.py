#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import os
from pathlib import Path


bench_root = Path(
    os.environ.get(
        "FRAPPE_BENCH_ROOT",
        "/home/frappe/frappe-bench",
    )
).resolve()

frappe_utils = (
    bench_root
    / "apps/frappe/realtime/utils.js"
)

frappe_authenticate = (
    bench_root
    / "apps/frappe/realtime/middlewares/authenticate.js"
)

frappe_index = (
    bench_root
    / "apps/frappe/realtime/index.js"
)

helpdesk_handlers = (
    bench_root
    / "apps/helpdesk/realtime/handlers.js"
)


expected_sha256 = {
    frappe_utils: (
        "f7224c92840b1cfaafa34b91dd808da4"
        "92fc7e454afd5db0a982481c36a17093"
    ),
    frappe_authenticate: (
        "3c153527523c584b04a465a1167d6fbc"
        "3c585e8e72c26eadf2d7b3c42d36ddc9"
    ),
    frappe_index: (
        "821c1d26404b02fae63fa8c6676c6c101"
        "88fdf3fd0c85a149c454e0934ab11a0"
    ),
    helpdesk_handlers: (
        "b743eb0379f037207b0a0f01b3a3b65e"
        "84c58369851670f75986072c8159ab54"
    ),
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def require_expected_source() -> None:
    failures = []

    for path, expected in expected_sha256.items():
        if not path.is_file():
            failures.append(
                {
                    "path": str(path),
                    "status": "MISSING",
                }
            )
            continue

        actual = file_sha256(path)

        print(
            {
                "check": "upstream-source-sha256",
                "path": str(path),
                "expected": expected,
                "actual": actual,
                "result": (
                    "PASS"
                    if actual == expected
                    else "FAIL"
                ),
            }
        )

        if actual != expected:
            failures.append(
                {
                    "path": str(path),
                    "expected": expected,
                    "actual": actual,
                    "status": "SHA256_MISMATCH",
                }
            )

    if failures:
        raise RuntimeError(
            {
                "frappe_realtime_compat": "REFUSED",
                "failures": failures,
            }
        )


def replace_once(
    source: str,
    old: str,
    new: str,
    *,
    label: str,
) -> str:
    count = source.count(old)

    if count != 1:
        raise RuntimeError(
            {
                "transformation": label,
                "expected_occurrences": 1,
                "actual_occurrences": count,
                "status": "REFUSED",
            }
        )

    return source.replace(
        old,
        new,
        1,
    )


require_expected_source()

utils_source = frappe_utils.read_text(
    encoding="utf-8"
)

authenticate_source = frappe_authenticate.read_text(
    encoding="utf-8"
)

index_source = frappe_index.read_text(
    encoding="utf-8"
)


utils_source = replace_once(
    utils_source,
    'const request = require("superagent");\n',
    (
        'const request = require("superagent");\n'
        'const { get_conf } = require("../node_utils");\n'
        "\n"
        "const conf = get_conf();\n"
    ),
    label="utils-load-common-config",
)

utils_source = replace_once(
    utils_source,
    "return socket.request.headers.origin + path;",
    (
        "if (conf.webserver_host && conf.webserver_port) {\n"
        "\t\tlet base = conf.webserver_host;\n"
        "\n"
        '\t\tif (base.indexOf("://") === -1) {\n'
        "\t\t\tbase = `http://${base}`;\n"
        "\t\t}\n"
        "\n"
        "\t\tconst url = new URL(base);\n"
        "\n"
        "\t\tif (!url.port) {\n"
        "\t\t\turl.port = conf.webserver_port;\n"
        "\t\t}\n"
        "\n"
        "\t\treturn url.origin + path;\n"
        "\t}\n"
        "\n"
        "\treturn socket.request.headers.origin + path;"
    ),
    label="utils-internal-webserver-url",
)


authenticate_source = replace_once(
    authenticate_source,
    (
        "let auth_req = request.get("
        'get_url(socket, "/api/method/frappe.realtime.get_user_info")'
        ");"
    ),
    (
        "let auth_req = request.get("
        'get_url(socket, "/api/method/frappe.realtime.get_user_info")'
        ");\n"
        '\t\tauth_req = auth_req.set("X-Frappe-Site-Name", '
        "get_site_name(socket));"
    ),
    label="authenticate-site-name-header",
)


index_source = replace_once(
    index_source,
    (
        'const frappe_handlers = require('
        '"./handlers/frappe_handlers");'
    ),
    (
        'const frappe_handlers = require('
        '"./handlers/frappe_handlers");\n'
        "const helpdesk_handlers = require("
        '"../../helpdesk/realtime/handlers");'
    ),
    label="index-load-helpdesk-handlers",
)

index_source = replace_once(
    index_source,
    "frappe_handlers(realtime, socket);",
    (
        "frappe_handlers(realtime, socket);\n"
        "\thelpdesk_handlers(socket);"
    ),
    label="index-register-helpdesk-handlers",
)


required_postconditions = [
    (
        frappe_utils,
        utils_source,
        "conf.webserver_host && conf.webserver_port",
    ),
    (
        frappe_authenticate,
        authenticate_source,
        '"X-Frappe-Site-Name"',
    ),
    (
        frappe_index,
        index_source,
        'require("../../helpdesk/realtime/handlers")',
    ),
    (
        frappe_index,
        index_source,
        "helpdesk_handlers(socket);",
    ),
    (
        frappe_index,
        index_source,
        'socket.on("open_in_editor"',
    ),
]

for path, source, required in required_postconditions:
    if required not in source:
        raise RuntimeError(
            {
                "path": str(path),
                "required_postcondition": required,
                "status": "REFUSED",
            }
        )


frappe_utils.write_text(
    utils_source,
    encoding="utf-8",
)

frappe_authenticate.write_text(
    authenticate_source,
    encoding="utf-8",
)

frappe_index.write_text(
    index_source,
    encoding="utf-8",
)


for path in (
    frappe_utils,
    frappe_authenticate,
    frappe_index,
):
    print(
        {
            "check": "patched-source-sha256",
            "path": str(path),
            "sha256": file_sha256(path),
            "result": "PASS",
        }
    )


print(
    {
        "frappe_version_contract": "v15.94.1",
        "helpdesk_version_contract": "v1.18.1",
        "source_guard": "SHA256",
        "open_in_editor_preserved": True,
        "frappe_realtime_compat": "PASS",
    }
)

print("FRAPPE_REALTIME_COMPAT_PATCH=PASS")
