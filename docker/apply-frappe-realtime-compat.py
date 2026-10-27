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

frappe_handlers = (
    bench_root
    / "apps/frappe/realtime/handlers/frappe_handlers.js"
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
    frappe_handlers: (
        "c8cde7c0124e03bfae975351c4e819be"
        "f116b1d05fa3dd2b7d8bdb0856c7dd41"
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

handlers_source = frappe_handlers.read_text(
    encoding="utf-8"
)

helpdesk_source = helpdesk_handlers.read_text(
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
        '\t\t\tbase = `http://${base}`;\n'
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

utils_source = replace_once(
    utils_source,
    "const partial_req = request.get(get_url(socket, path));",
    (
        'if (!socket || typeof socket.site_name !== "string" '
        '|| !socket.site_name.trim()) {\n'
        '\t\tthrow new Error("Missing authenticated Frappe site");\n'
        '\t}\n'
        '\tconst partial_req = request.get(get_url(socket, path))\n'
        '\t\t.set("X-Frappe-Site-Name", socket.site_name);'
    ),
    label="utils-realtime-callback-site-header",
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

handlers_source = replace_once(
    handlers_source,
    'socket.on("doc_subscribe", function (doctype, docname) {',
    (
        'socket.on("doc_subscribe", function (doctype, docname) {\n'
        '       if (doctype === "HD Ticket") {\n'
        '           can_subscribe_hd_ticket_native({\n'
        '               socket,\n'
        '               doctype,\n'
        '               docname,\n'
        '               callback: () => {\n'
        '                   socket.join(doc_room(doctype, docname));\n'
        '               },\n'
        '           });\n'
        '           return;\n'
        '       }'
    ),
    label="native-hd-ticket-document-subscription-policy",
)

handlers_source = replace_once(
    handlers_source,
    (
        'socket.on("doc_open", function (doctype, docname) {\n'
        '\t\tcan_subscribe_doc({'
    ),
    (
        'socket.on("doc_open", function (doctype, docname) {\n'
        '\t\tconst authorize_doc_open = doctype === "HD Ticket"\n'
        '\t\t\t? can_subscribe_hd_ticket_native\n'
        '\t\t\t: can_subscribe_doc;\n'
        '\t\tauthorize_doc_open({'
    ),
    label="native-hd-ticket-doc-open-policy",
)


# C3.152 — Native HD Ticket pending doc_subscribe lifecycle.

handlers_source = replace_once(
    handlers_source,
    "function frappe_handlers(realtime, socket) {\n",
    (
        "function frappe_handlers(realtime, socket) {\n"
        "\tconst pendingNativeTicketRooms = new Map();\n"
    ),
    label="native-hd-ticket-pending-subscription-registry",
)

handlers_source = replace_once(
    handlers_source,
    "           can_subscribe_hd_ticket_native({\n",
    (
        '           const room = doc_room(doctype, docname);\n'
        '           const token = Symbol("doc_subscribe");\n'
        '           pendingNativeTicketRooms.set(room, token);\n'
        '           can_subscribe_hd_ticket_native({\n'
    ),
    label="native-hd-ticket-subscription-token",
)

handlers_source = replace_once(
    handlers_source,
    (
        '               callback: () => {\n'
        '                   socket.join(doc_room(doctype, docname));'
    ),
    (
        '               callback: () => {\n'
        '                   if (pendingNativeTicketRooms.get(room) !== token) return;\n'
        '                   pendingNativeTicketRooms.delete(room);\n'
        '                   if (socket.connected !== true) return;\n'
        '                   socket.join(room);'
    ),
    label="native-hd-ticket-subscription-late-approval-gate",
)

handlers_source = replace_once(
    handlers_source,
    'socket.on("doc_unsubscribe", function (doctype, docname) {',
    (
        'socket.on("doc_unsubscribe", function (doctype, docname) {\n'
        '\t\tif (doctype === "HD Ticket") '
        'pendingNativeTicketRooms.delete(doc_room(doctype, docname));'
    ),
    label="native-hd-ticket-unsubscribe-cancellation",
)

handlers_source = replace_once(
    handlers_source,
    'socket.on("disconnect", () => {',
    (
        'socket.on("disconnect", () => {\n'
        '\t\tpendingNativeTicketRooms.clear();'
    ),
    label="native-hd-ticket-disconnect-cancellation",
)



handlers_source = replace_once(
    handlers_source,
    "function can_subscribe_doc(args) {\n",
    """function can_subscribe_hd_ticket_native(args) {
        if (!args || !args.socket || !args.docname || args.doctype !== "HD Ticket") {
                if (args && args.onComplete) args.onComplete(false);
                return;
        }

        let completed = false;

        function complete(allowed, err, res) {
                if (completed) return;
                completed = true;

                try {
                        if (allowed && args.callback) {
                                args.callback(err, res);
                        }
                } finally {
                        if (args.onComplete) {
                                args.onComplete(allowed);
                        }
                }
        }

        try {
                frappe_request(
                        "/api/method/telephony.realtime_ticket_authorization.require_ticket_realtime_access",
                        args.socket
                )
                        .type("form")
                        .query({
                                ticket_name: args.docname,
                                channel: "native_doc",
                        })
                        .end(function (err, res) {
                                const allowed = Boolean(
                                        !err &&
                                        res &&
                                        res.status === 200 &&
                                        res.body &&
                                        res.body.message === true
                                );

                                complete(allowed, err, res);
                        });
        } catch (error) {
                complete(false, error, null);
        }
}

function can_subscribe_doc(args) {
""",
    label="native-hd-ticket-authorisation-checker",
)


helpdesk_source = replace_once(
    helpdesk_source,
    "function helpdesk_handlers(socket) {",
    """const { frappe_request } = require("../../frappe/realtime/utils");

function can_view_helpdesk_ticket(socket, ticket_id) {
  return new Promise((resolve) => {
    if (typeof ticket_id !== "string" || !ticket_id.trim()) {
      resolve(false);
      return;
    }

    try {
      frappe_request(
        "/api/method/telephony.realtime_ticket_authorization.require_ticket_realtime_access",
        socket
      )
        .type("form")
        .query({
          ticket_name: ticket_id,
          channel: "helpdesk_ticket",
        })
        .end((err, res) => {
          resolve(Boolean(
            !err &&
            res &&
            res.status === 200 &&
            res.body &&
            res.body.message === true
          ));
        });
    } catch (error) {
      resolve(false);
    }
  });
}

function helpdesk_handlers(socket) {""",
    label="helpdesk-ticket-authorisation-helper",
)

helpdesk_source = replace_once(
    helpdesk_source,
    'socket.on("view_ticket", (ticket_id) => {',
    'socket.on("view_ticket", async (ticket_id) => {',
    label="helpdesk-view-ticket-async-handler",
)

helpdesk_source = replace_once(
    helpdesk_source,
    (
        'socket.on("view_ticket", async (ticket_id) => {\n'
        '    if (!ticket_id) return;'
    ),
    (
        'socket.on("view_ticket", async (ticket_id) => {\n'
        '    if (!ticket_id) return;\n'
        '    if (!(await can_view_helpdesk_ticket(socket, ticket_id))) return;'
    ),
    label="helpdesk-view-ticket-permission-gate",
)

helpdesk_source = replace_once(
    helpdesk_source,
    (
        'socket.on("ticket_get_viewers", (ticket_id) => {\n'
        '    if (!ticket_id) return;'
    ),
    (
        'socket.on("ticket_get_viewers", async (ticket_id) => {\n'
        '    if (!ticket_id) return;\n'
        '    if (!(await can_view_helpdesk_ticket(socket, ticket_id))) return;'
    ),
    label="helpdesk-ticket-viewer-query-permission-gate",
)

helpdesk_source = replace_once(
    helpdesk_source,
    """  socket.on("notify_ticket_update", (ticket_id, field, value) => {
    if (!(ticket_id && field)) return;
    const ticket_room = open_doc_room("HD Ticket", ticket_id);
    socket.to(ticket_room).emit("ticket_update", {
      ticket_id,
      user: socket.user,
      field,
      value,
    });
  });
""",
    "",
    label="helpdesk-disable-untrusted-field-update-broadcast",
)

helpdesk_source = replace_once(
    helpdesk_source,
    (
        'socket.on("stop_view_ticket", (ticket_id) => {\n'
        '    if (!ticket_id) return;\n'
        '    const room = open_doc_room("HD Ticket", ticket_id);\n'
        '    socket.leave(room);'
    ),
    (
        'socket.on("stop_view_ticket", (ticket_id) => {\n'
        '    if (!ticket_id) return;\n'
        '    const room = open_doc_room("HD Ticket", ticket_id);\n'
        '    const members = socket.nsp.adapter.rooms.get(room);\n'
        '    if (!members || !members.has(socket.id)) return;\n'
        '    socket.leave(room);'
    ),
    label="helpdesk-stop-view-ticket-membership-gate",
)

helpdesk_source = replace_once(
    helpdesk_source,
    (
        'socket.on("helpdesk_ticket_typing", (ticket_id) => {\n'
        '    if (!ticket_id) return;\n'
        '    const ticket_room = open_doc_room("HD Ticket", ticket_id);'
    ),
    (
        'socket.on("helpdesk_ticket_typing", async (ticket_id) => {\n'
        '    if (!ticket_id) return;\n'
        '    const ticket_room = open_doc_room("HD Ticket", ticket_id);\n'
        '    const members = socket.nsp.adapter.rooms.get(ticket_room);\n'
        '    if (!members || !members.has(socket.id)) return;\n'
        '    if (!(await can_view_helpdesk_ticket(socket, ticket_id))) return;'
    ),
    label="helpdesk-typing-start-authorisation-gate",
)

helpdesk_source = replace_once(
    helpdesk_source,
    (
        'socket.on("helpdesk_ticket_typing_stopped", (ticket_id) => {\n'
        '    if (!ticket_id) return;\n'
        '    const ticket_room = open_doc_room("HD Ticket", ticket_id);'
    ),
    (
        'socket.on("helpdesk_ticket_typing_stopped", async (ticket_id) => {\n'
        '    if (!ticket_id) return;\n'
        '    const ticket_room = open_doc_room("HD Ticket", ticket_id);\n'
        '    const members = socket.nsp.adapter.rooms.get(ticket_room);\n'
        '    if (!members || !members.has(socket.id)) return;\n'
        '    if (!(await can_view_helpdesk_ticket(socket, ticket_id))) return;'
    ),
    label="helpdesk-typing-stop-authorisation-gate",
)

for event in (
    "helpdesk_ticket_typing",
    "helpdesk_ticket_typing_stopped",
):
    helpdesk_source = replace_once(
        helpdesk_source,
        (
            f'socket.on("{event}", async (ticket_id) => {{\n'
            '    if (!ticket_id) return;\n'
            '    const ticket_room = open_doc_room("HD Ticket", ticket_id);\n'
            '    const members = socket.nsp.adapter.rooms.get(ticket_room);\n'
            '    if (!members || !members.has(socket.id)) return;\n'
            '    if (!(await can_view_helpdesk_ticket(socket, ticket_id))) return;'
        ),
        (
            f'socket.on("{event}", async (ticket_id) => {{\n'
            '    if (!ticket_id) return;\n'
            '    const ticket_room = open_doc_room("HD Ticket", ticket_id);\n'
            '    const members = socket.nsp.adapter.rooms.get(ticket_room);\n'
            '    if (!members || !members.has(socket.id)) return;\n'
            '    if (!(await can_view_helpdesk_ticket(socket, ticket_id))) return;\n'
            '    if (!socket.nsp.adapter.rooms.get(ticket_room)?.has(socket.id)) return;'
        ),
        label=f"helpdesk-{event}-post-authorisation-membership",
    )

helpdesk_source = replace_once(
    helpdesk_source,
    "function helpdesk_handlers(socket) {",
    (
        "function helpdesk_handlers(socket) {\n"
        "  const pendingTicketViews = new Map();\n"
        '  socket.on("disconnect", () => pendingTicketViews.clear());'
    ),
    label="helpdesk-pending-view-registry",
)

helpdesk_source = replace_once(
    helpdesk_source,
    (
        'socket.on("view_ticket", async (ticket_id) => {\n'
        '    if (!ticket_id) return;\n'
        '    if (!(await can_view_helpdesk_ticket(socket, ticket_id))) return;\n'
        '    const room = open_doc_room("HD Ticket", ticket_id);\n'
        '    socket.join(room);'
    ),
    (
        'socket.on("view_ticket", async (ticket_id) => {\n'
        '    if (!ticket_id) return;\n'
        '    const request = Symbol("view_ticket");\n'
        '    pendingTicketViews.set(ticket_id, request);\n'
        '    const allowed = await can_view_helpdesk_ticket(socket, ticket_id);\n'
        '    if (pendingTicketViews.get(ticket_id) !== request) return;\n'
        '    pendingTicketViews.delete(ticket_id);\n'
        '    if (!allowed || socket.connected !== true) return;\n'
        '    const room = open_doc_room("HD Ticket", ticket_id);\n'
        '    socket.join(room);'
    ),
    label="helpdesk-view-ticket-pending-request-validation",
)

helpdesk_source = replace_once(
    helpdesk_source,
    (
        'socket.on("stop_view_ticket", (ticket_id) => {\n'
        '    if (!ticket_id) return;\n'
        '    const room = open_doc_room("HD Ticket", ticket_id);'
    ),
    (
        'socket.on("stop_view_ticket", (ticket_id) => {\n'
        '    if (!ticket_id) return;\n'
        '    pendingTicketViews.delete(ticket_id);\n'
        '    const room = open_doc_room("HD Ticket", ticket_id);'
    ),
    label="helpdesk-stop-view-cancels-pending-request",
)


# C3.153 — Native HD Ticket pending doc_open lifecycle.

handlers_source = replace_once(
    handlers_source,
    (
        'socket.on("doc_open", function (doctype, docname) {\n'
        '\t\tconst authorize_doc_open = doctype === "HD Ticket"'
    ),
    (
        'socket.on("doc_open", function (doctype, docname) {\n'
        '\t\tconst nativeTicketRoom = doctype === "HD Ticket"\n'
        '\t\t\t? open_doc_room(doctype, docname)\n'
        '\t\t\t: null;\n'
        '\t\tconst nativeTicketToken = nativeTicketRoom ? Symbol("doc_open") : null;\n'
        '\t\tif (nativeTicketToken) pendingNativeTicketRooms.set(nativeTicketRoom, nativeTicketToken);\n'
        '\t\tconst authorize_doc_open = doctype === "HD Ticket"'
    ),
    label="native-hd-ticket-doc-open-pending-token",
)

handlers_source = replace_once(
    handlers_source,
    (
        'callback: () => {\n'
        '\t\t\t\tlet room = open_doc_room(doctype, docname);'
    ),
    (
        'callback: () => {\n'
        '\t\t\t\tif (nativeTicketRoom) {\n'
        '\t\t\t\t\tif (pendingNativeTicketRooms.get(nativeTicketRoom) !== nativeTicketToken) return;\n'
        '\t\t\t\t\tpendingNativeTicketRooms.delete(nativeTicketRoom);\n'
        '\t\t\t\t\tif (socket.connected !== true) return;\n'
        '\t\t\t\t}\n'
        '\t\t\t\tlet room = open_doc_room(doctype, docname);'
    ),
    label="native-hd-ticket-doc-open-late-approval-gate",
)

handlers_source = replace_once(
    handlers_source,
    'socket.on("doc_close", function (doctype, docname) {',
    (
        'socket.on("doc_close", function (doctype, docname) {\n'
        '\t\tif (doctype === "HD Ticket") pendingNativeTicketRooms.delete(open_doc_room(doctype, docname));'
    ),
    label="native-hd-ticket-doc-close-cancellation",
)


# C3.156 — Clean up completed native HD Ticket authorisation requests.

handlers_source = replace_once(
    handlers_source,
    (
        '               callback: () => {\n'
        '                   if (pendingNativeTicketRooms.get(room) !== token) return;'
    ),
    (
        '               onComplete: () => {\n'
        '                   if (pendingNativeTicketRooms.get(room) === token) {\n'
        '                       pendingNativeTicketRooms.delete(room);\n'
        '                   }\n'
        '               },\n'
        '               callback: () => {\n'
        '                   if (pendingNativeTicketRooms.get(room) !== token) return;'
    ),
    label="native-hd-ticket-doc-subscribe-completion-cleanup",
)

handlers_source = replace_once(
    handlers_source,
    (
        'authorize_doc_open({\n'
        '\t\t\tsocket,\n'
        '\t\t\tdoctype,\n'
        '\t\t\tdocname,\n'
    ),
    (
        'authorize_doc_open({\n'
        '\t\t\tsocket,\n'
        '\t\t\tdoctype,\n'
        '\t\t\tdocname,\n'
        '\t\t\tonComplete: () => {\n'
        '\t\t\t\tif (nativeTicketRoom && pendingNativeTicketRooms.get(nativeTicketRoom) === nativeTicketToken) {\n'
        '\t\t\t\t\tpendingNativeTicketRooms.delete(nativeTicketRoom);\n'
        '\t\t\t\t}\n'
        '\t\t\t},\n'
    ),
    label="native-hd-ticket-doc-open-completion-cleanup",
)

# C3.225 — Reauthorise recipients before protected ticket delivery.

utils_source = replace_once(
    utils_source,
    "module.exports = {",
    """function ticket_access_allowed(socket, ticket_name, channel) {
    return new Promise((resolve) => {
        if (
            !socket ||
            socket.connected !== true ||
            typeof ticket_name !== "string" ||
            !ticket_name.trim() ||
            !["native_doc", "helpdesk_ticket"].includes(channel)
        ) {
            resolve(false);
            return;
        }

        try {
            frappe_request(
                "/api/method/telephony.realtime_ticket_authorization.require_ticket_realtime_access",
                socket
            )
                .type("form")
                .query({ ticket_name, channel })
                .timeout({ response: 2000, deadline: 5000 })
                .end((err, res) => {
                    resolve(Boolean(
                        !err &&
                        res &&
                        res.status === 200 &&
                        res.body &&
                        res.body.message === true
                    ));
                });
        } catch (error) {
            resolve(false);
        }
    });
}

async function authorized_ticket_room_members(
    namespace,
    room,
    ticket_name,
    channel,
    evict_denied = true
) {
    if (
        !namespace ||
        !namespace.adapter ||
        !namespace.adapter.rooms ||
        !namespace.sockets ||
        typeof room !== "string"
    ) {
        return [];
    }

    const ids = Array.from(
        namespace.adapter.rooms.get(room) || []
    );

    const checked = await Promise.all(ids.map(async (id) => {
        const socket = namespace.sockets.get(id);

        if (
            !socket ||
            socket.connected !== true ||
            !socket.rooms ||
            !socket.rooms.has(room)
        ) {
            return null;
        }

        const allowed = await ticket_access_allowed(
            socket,
            ticket_name,
            channel
        );

        if (!allowed) {
            if (evict_denied && socket.connected && socket.rooms.has(room)) {
                socket.leave(room);
            }
            return null;
        }

        if (
            socket.connected !== true ||
            !socket.rooms.has(room)
        ) {
            return null;
        }

        return socket;
    }));

    return checked.filter(Boolean);
}

async function deliver_authorized_ticket_room(
    namespace,
    room,
    ticket_name,
    channel,
    event,
    payload,
    exclude_socket_id = null
) {
    const recipients = await authorized_ticket_room_members(
        namespace,
        room,
        ticket_name,
        channel
    );

    for (const socket of recipients) {
        if (
            socket.id !== exclude_socket_id &&
            socket.connected === true &&
            socket.rooms.has(room)
        ) {
            socket.emit(event, payload);
        }
    }

    return recipients.length;
}

module.exports = {""",
    label="realtime-recipient-authorisation-functions",
)

utils_source = replace_once(
    utils_source,
    "frappe_request,\n",
    (
        "frappe_request,\n"
        "\tticket_access_allowed,\n"
        "\tauthorized_ticket_room_members,\n"
        "\tdeliver_authorized_ticket_room,\n"
    ),
    label="realtime-recipient-authorisation-exports",
)

# C3.225b — Protect outbound HD Ticket realtime delivery.

# 1. Redis -> Socket.IO protected document rooms.

index_source = replace_once(
    index_source,
    'const http = require("node:http");',
    (
        'const http = require("node:http");\n'
        'const { deliver_authorized_ticket_room } = require("./utils");'
    ),
    label="index-load-protected-delivery",
)

index_source = replace_once(
    index_source,
    'subscriber.subscribe("events", (message) => {',
    'subscriber.subscribe("events", async (message) => {',
    label="index-async-redis-delivery",
)

index_source = replace_once(
    index_source,
    'io.of(namespace).to(message.room).emit(message.event, message.message);',
    """const nativePrefix = "doc:HD Ticket/";
                    const helpdeskPrefix = "open_doc:HD Ticket/";
                    const native = typeof message.room === "string" &&
                        message.room.startsWith(nativePrefix);
                    const helpdesk = typeof message.room === "string" &&
                        message.room.startsWith(helpdeskPrefix);

                    if (native || helpdesk) {
                        const ticket = message.room.slice(
                            (native ? nativePrefix : helpdeskPrefix).length
                        );

                        if (ticket) {
                            try {
                                await deliver_authorized_ticket_room(
                                    io.of(namespace),
                                    message.room,
                                    ticket,
                                    native ? "native_doc" : "helpdesk_ticket",
                                    message.event,
                                    message.message
                                );
                            } catch (error) {
                                console.error(
                                    "Protected HD Ticket delivery refused"
                                );
                            }
                        }
                    } else {
                        io.of(namespace).to(message.room).emit(
                            message.event,
                            message.message
                        );
                    }""",
    label="index-protected-ticket-redis-delivery",
)


# 2. Native document viewer notifications.

handlers_source = replace_once(
    handlers_source,
    'const { frappe_request } = require("../utils");',
    (
        'const { frappe_request, authorized_ticket_room_members } '
        '= require("../utils");'
    ),
    label="native-load-recipient-authorisation",
)

handlers_source = replace_once(
    handlers_source,
    "function notify_subscribed_doc_users(args) {",
    "async function notify_subscribed_doc_users(args) {",
    label="native-async-viewer-notification",
)

handlers_source = replace_once(
    handlers_source,
    "const clients = Array.from(socket.nsp.adapter.rooms.get(room) || []);",
    """if (args.doctype === "HD Ticket") {
                const recipients = await authorized_ticket_room_members(
                    socket.nsp,
                    room,
                    args.docname,
                    "native_doc",
                    false // This room also contains authorised Helpdesk viewers.
                );

                const users = Array.from(
                    new Set(recipients.map((recipient) => recipient.user))
                );

                if (users.length === 1 && users[0] === socket.user) {
                    return;
                }

                const payload = {
                    doctype: args.doctype,
                    docname: args.docname,
                    users,
                };

                for (const recipient of recipients) {
                    if (
                        recipient.connected === true &&
                        recipient.rooms.has(room)
                    ) {
                        recipient.emit("doc_viewers", payload);
                    }
                }
                return;
        }

        const clients = Array.from(socket.nsp.adapter.rooms.get(room) || []);""",
    label="native-protected-viewer-delivery",
)


# 3. Helpdesk direct outbound events.

helpdesk_source = replace_once(
    helpdesk_source,
    'const { frappe_request } = require("../../frappe/realtime/utils");',
    (
        'const { frappe_request, ticket_access_allowed, '
        'authorized_ticket_room_members, deliver_authorized_ticket_room } = '
        'require("../../frappe/realtime/utils");'
    ),
    label="helpdesk-load-recipient-authorisation",
)

for event in (
    "helpdesk_ticket_typing",
    "helpdesk_ticket_typing_stopped",
):
    helpdesk_source = replace_once(
        helpdesk_source,
        (
            f'    socket.to(ticket_room).emit("{event}", {{\n'
            '      ticket_id,\n'
            '      user: socket.user,\n'
            '    });'
        ),
        (
            '    await deliver_authorized_ticket_room(\n'
            '      socket.nsp,\n'
            '      ticket_room,\n'
            '      ticket_id,\n'
            '      "helpdesk_ticket",\n'
            f'      "{event}",\n'
            '      { ticket_id, user: socket.user },\n'
            '      socket.id\n'
            '    );'
        ),
        label=f"helpdesk-protected-{event}-delivery",
    )

helpdesk_source = replace_once(
    helpdesk_source,
    "function notify_ticket_viewers(args) {",
    "async function notify_ticket_viewers(args) {",
    label="helpdesk-async-viewer-notification",
)

helpdesk_source = replace_once(
    helpdesk_source,
    "const clients = Array.from(socket.nsp.adapter.rooms.get(ticket_room) || []);",
    """const authorizedClients = await authorized_ticket_room_members(
    socket.nsp,
    ticket_room,
    ticket_id,
    "helpdesk_ticket"
  );

  const clients = authorizedClients.map((client) => client.id);""",
    label="helpdesk-authorized-viewer-list",
)

helpdesk_source = replace_once(
    helpdesk_source,
    """  const target_room = args.toUser
    ? user_room(args.socket.user) // Send to specific user only
    : ticket_room; // Send to all viewers in the ticket room

  // Emit the notification with current viewers list
  socket.nsp.to(target_room).emit("ticket_viewers", {
    ticket_id,
    users: JSON.stringify(Array.from(new Set(users))), // Remove duplicate users
    total_viewers: Array.from(new Set(users)).length,
  });""",
    """  const payload = {
    ticket_id,
    users: JSON.stringify(Array.from(new Set(users))),
    total_viewers: Array.from(new Set(users)).length,
  };

  if (args.toUser) {
    const allowed = await ticket_access_allowed(
      socket,
      ticket_id,
      "helpdesk_ticket"
    );

    if (!allowed || socket.connected !== true) return;

    socket.emit("ticket_viewers", payload);
    return;
  }

  for (const recipient of authorizedClients) {
    if (
      recipient.connected === true &&
      recipient.rooms.has(ticket_room)
    ) {
      recipient.emit("ticket_viewers", payload);
    }
  }""",
    label="helpdesk-protected-viewer-delivery",
)



# C3.238 — Restrict broad HD Ticket DocType subscription and outbound delivery.

handlers_source = replace_once(
    handlers_source,
    '\tsocket.on("doctype_subscribe", function (doctype) {\n\t\tcan_subscribe_doctype({\n\t\t\tsocket,\n\t\t\tdoctype,\n\t\t\tcallback: () => {\n\t\t\t\tsocket.join(doctype_room(doctype));\n\t\t\t},\n\t\t});\n\t});',
    '\tlet pendingHDTicketDoctypeSubscription = null;\n\tsocket.on("doctype_subscribe", function (doctype) {\n\t\tif (doctype === "HD Ticket") {\n\t\t\t// A DocType room spans every customer. Never admit Website Users.\n\t\t\tif (socket.user_type !== "System User" || socket.connected !== true) return;\n\t\t\tconst token = Symbol("hd_ticket_doctype_subscribe");\n\t\t\tpendingHDTicketDoctypeSubscription = token;\n\t\t\tcan_subscribe_doctype({\n\t\t\t\tsocket,\n\t\t\t\tdoctype,\n\t\t\t\tcallback: () => {\n\t\t\t\t\tif (pendingHDTicketDoctypeSubscription !== token) return;\n\t\t\t\t\tpendingHDTicketDoctypeSubscription = null;\n\t\t\t\t\tif (socket.connected !== true || socket.user_type !== "System User") return;\n\t\t\t\t\tsocket.join(doctype_room(doctype));\n\t\t\t\t},\n\t\t\t});\n\t\t\treturn;\n\t\t}\n\t\tcan_subscribe_doctype({\n\t\t\tsocket,\n\t\tdoctype,\n\t\t\tcallback: () => {\n\t\t\t\tsocket.join(doctype_room(doctype));\n\t\t\t},\n\t\t});\n\t});',
    label='hd-ticket-doctype-system-user-subscribe',
)

handlers_source = replace_once(
    handlers_source,
    '\tsocket.on("doctype_unsubscribe", function (doctype) {\n\t\tsocket.leave(doctype_room(doctype));\n\t});',
    '\tsocket.on("doctype_unsubscribe", function (doctype) {\n\t\tif (doctype === "HD Ticket") pendingHDTicketDoctypeSubscription = null;\n\t\tsocket.leave(doctype_room(doctype));\n\t});',
    label='hd-ticket-doctype-cancel-unsubscribe',
)

handlers_source = replace_once(
    handlers_source,
    '\tsocket.on("disconnect", () => {\n\t\tpendingNativeTicketRooms.clear();',
    '\tsocket.on("disconnect", () => {\n\t\tpendingHDTicketDoctypeSubscription = null;\n\t\tpendingNativeTicketRooms.clear();',
    label='hd-ticket-doctype-cancel-disconnect',
)

utils_source = replace_once(
    utils_source,
    'module.exports = {',
    '// A DocType room is unscoped: only currently authenticated System Users with\n// current HD Ticket read permission may receive any of its events.\nfunction realtime_api_message(socket, path, params = null) {\n    return new Promise((resolve) => {\n        try {\n            let request = frappe_request(path, socket)\n                .type("form")\n                .timeout({ response: 2000, deadline: 5000 });\n            if (params) request = request.query(params);\n            request.end((err, res) => {\n                resolve(!err && res && res.status === 200 && res.body\n                    ? res.body.message : null);\n            });\n        } catch (error) {\n            resolve(null);\n        }\n    });\n}\n\nasync function hd_ticket_doctype_access_allowed(socket) {\n    if (!socket || socket.connected !== true ||\n        socket.user_type !== "System User" ||\n        typeof socket.user !== "string" || !socket.user) return false;\n\n    // Re-check live session identity: socket.user_type is only a connect-time value.\n    const identity = await realtime_api_message(\n        socket, "/api/method/frappe.realtime.get_user_info"\n    );\n    if (!identity || identity.user !== socket.user ||\n        identity.user_type !== "System User" || socket.connected !== true) return false;\n\n    return (await realtime_api_message(\n        socket,\n        "/api/method/frappe.realtime.can_subscribe_doctype",\n        { doctype: "HD Ticket" }\n    )) === true;\n}\n\nasync function deliver_authorized_hd_ticket_doctype(namespace, room, event, payload) {\n    if (room !== "doctype:HD Ticket" || !namespace ||\n        !namespace.adapter || !namespace.adapter.rooms || !namespace.sockets) return 0;\n\n    const ids = Array.from(namespace.adapter.rooms.get(room) || []);\n    const outcomes = await Promise.all(ids.map(async (id) => {\n        const socket = namespace.sockets.get(id);\n        if (!socket || socket.connected !== true ||\n            !socket.rooms || !socket.rooms.has(room)) return false;\n\n        const allowed = await hd_ticket_doctype_access_allowed(socket);\n        if (!allowed) {\n            if (socket.connected === true && socket.rooms.has(room)) socket.leave(room);\n            return false;\n        }\n        if (socket.connected !== true || !socket.rooms.has(room)) return false;\n        socket.emit(event, payload);\n        return true;\n    }));\n    return outcomes.filter(Boolean).length;\n}\n\nmodule.exports = {',
    label='hd-ticket-doctype-recipient-helper',
)

utils_source = replace_once(
    utils_source,
    '\tdeliver_authorized_ticket_room,\n',
    '\tdeliver_authorized_ticket_room,\n\thd_ticket_doctype_access_allowed,\n\tdeliver_authorized_hd_ticket_doctype,\n',
    label='hd-ticket-doctype-recipient-exports',
)

index_source = replace_once(
    index_source,
    '                    } else {\n                        io.of(namespace).to(message.room).emit(\n                            message.event,\n                            message.message\n                        );\n                    }',
    '                    } else if (message.room === "doctype:HD Ticket") {\n                        try {\n                            await deliver_authorized_hd_ticket_doctype(\n                                io.of(namespace), message.room,\n                                message.event, message.message\n                            );\n                        } catch (error) {\n                            console.error("Protected HD Ticket DocType delivery refused");\n                        }\n                    } else {\n                        io.of(namespace).to(message.room).emit(\n                            message.event,\n                            message.message\n                        );\n                    }',
    label='hd-ticket-doctype-redis-fail-closed',
)

index_source = replace_once(
    index_source,
    'deliver_authorized_ticket_room } =',
    'deliver_authorized_ticket_room, deliver_authorized_hd_ticket_doctype } =',
    label='hd-ticket-doctype-redis-import',
)

# C3.245 — Explicit Telectro internal authority for unscoped HD Ticket rooms.
# The existing C3.238 checks guard only User Type / general DocType read.

handlers_source = replace_once(
    handlers_source,
    'const { frappe_request, authorized_ticket_room_members } = require("../utils");',
    'const { frappe_request, authorized_ticket_room_members, hd_ticket_doctype_access_allowed } = require("../utils");',
    label="hd-ticket-doctype-internal-helper-import",
)

handlers_source = replace_once(
    handlers_source,
    '''	let pendingHDTicketDoctypeSubscription = null;
	socket.on("doctype_subscribe", function (doctype) {
		if (doctype === "HD Ticket") {
			// A DocType room spans every customer. Never admit Website Users.
			if (socket.user_type !== "System User" || socket.connected !== true) return;
			const token = Symbol("hd_ticket_doctype_subscribe");
			pendingHDTicketDoctypeSubscription = token;
			can_subscribe_doctype({
				socket,
				doctype,
				callback: () => {
					if (pendingHDTicketDoctypeSubscription !== token) return;
					pendingHDTicketDoctypeSubscription = null;
					if (socket.connected !== true || socket.user_type !== "System User") return;
					socket.join(doctype_room(doctype));
				},
			});
			return;
		}
		can_subscribe_doctype({
			socket,
		doctype,
			callback: () => {
				socket.join(doctype_room(doctype));
			},
		});
	});''',
    '''	let pendingHDTicketDoctypeSubscription = null;
	socket.on("doctype_subscribe", function (doctype) {
		if (doctype === "HD Ticket") {
			if (socket.user_type !== "System User" || socket.connected !== true) return;
			const token = Symbol("hd_ticket_doctype_subscribe");
			pendingHDTicketDoctypeSubscription = token;
			Promise.resolve()
				.then(() => hd_ticket_doctype_access_allowed(socket))
				.then((allowed) => {
					if (pendingHDTicketDoctypeSubscription !== token) return;
					pendingHDTicketDoctypeSubscription = null;
					if (allowed && socket.connected === true && socket.user_type === "System User") {
						socket.join(doctype_room(doctype));
					}
				})
				.catch(() => {
					if (pendingHDTicketDoctypeSubscription === token) pendingHDTicketDoctypeSubscription = null;
				});
			return;
		}
		can_subscribe_doctype({
			socket,
			doctype,
			callback: () => {
				socket.join(doctype_room(doctype));
			},
		});
	});''',
    label="hd-ticket-doctype-internal-only-subscription",
)

utils_source = replace_once(
    utils_source,
    '''    return (await realtime_api_message(
        socket,
        "/api/method/frappe.realtime.can_subscribe_doctype",
        { doctype: "HD Ticket" }
    )) === true;''',
    '''    return (await realtime_api_message(
        socket,
        "/api/method/telephony.realtime_ticket_authorization.require_internal_hd_ticket_doctype_realtime_access"
    )) === true;''',
    label="hd-ticket-doctype-explicit-internal-backend-authority",
)

required_postconditions = [
    (
        frappe_utils,
        utils_source,
        "/api/method/telephony.realtime_ticket_authorization.require_internal_hd_ticket_doctype_realtime_access",
    ),
    (
        frappe_handlers,
        handlers_source,
        "hd_ticket_doctype_access_allowed(socket)",
    ),
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
    (
        frappe_handlers,
        handlers_source,
        'if (doctype === "HD Ticket")',
    ),
    (
        frappe_handlers,
        handlers_source,
        "can_subscribe_hd_ticket_native(args)",
    ),
    (
        frappe_handlers,
        handlers_source,
        'channel: "native_doc"',
    ),
    (
        frappe_handlers,
        handlers_source,
        "res.body.message === true",
    ),
    (
        helpdesk_handlers,
        helpdesk_source,
        'channel: "helpdesk_ticket"',
    ),
    (
        helpdesk_handlers,
        helpdesk_source,
        "res.body.message === true",
    ),
    (
        helpdesk_handlers,
        helpdesk_source,
        (
            'socket.on("view_ticket", async (ticket_id) => {\n'
            '    if (!ticket_id) return;\n'
            '    const request = Symbol("view_ticket");\n'
            '    pendingTicketViews.set(ticket_id, request);\n'
            '    const allowed = await can_view_helpdesk_ticket(socket, ticket_id);\n'
            '    if (pendingTicketViews.get(ticket_id) !== request) return;\n'
            '    pendingTicketViews.delete(ticket_id);\n'
            '    if (!allowed || socket.connected !== true) return;'
        ),
    ),
    (
        helpdesk_handlers,
        helpdesk_source,
        'socket.on("disconnect", () => pendingTicketViews.clear());',
    ),
    (
        helpdesk_handlers,
        helpdesk_source,
        (
            'socket.on("ticket_get_viewers", async (ticket_id) => {\n'
            '    if (!ticket_id) return;\n'
            '    if (!(await can_view_helpdesk_ticket(socket, ticket_id))) return;'
        ),
    ),
    (
        helpdesk_handlers,
        helpdesk_source,
        (
            'socket.on("stop_view_ticket", (ticket_id) => {\n'
            '    if (!ticket_id) return;\n'
            '    pendingTicketViews.delete(ticket_id);\n'
            '    const room = open_doc_room("HD Ticket", ticket_id);\n'
            '    const members = socket.nsp.adapter.rooms.get(room);\n'
            '    if (!members || !members.has(socket.id)) return;'
        ),
    ),
    (
        helpdesk_handlers,
        helpdesk_source,
        (
            'socket.on("helpdesk_ticket_typing", async (ticket_id) => {\n'
            '    if (!ticket_id) return;\n'
            '    const ticket_room = open_doc_room("HD Ticket", ticket_id);\n'
            '    const members = socket.nsp.adapter.rooms.get(ticket_room);\n'
            '    if (!members || !members.has(socket.id)) return;\n'
            '    if (!(await can_view_helpdesk_ticket(socket, ticket_id))) return;'
        ),
    ),
    (
        helpdesk_handlers,
        helpdesk_source,
        (
            'socket.on("helpdesk_ticket_typing_stopped", async (ticket_id) => {\n'
            '    if (!ticket_id) return;\n'
            '    const ticket_room = open_doc_room("HD Ticket", ticket_id);\n'
            '    const members = socket.nsp.adapter.rooms.get(ticket_room);\n'
            '    if (!members || !members.has(socket.id)) return;\n'
            '    if (!(await can_view_helpdesk_ticket(socket, ticket_id))) return;'
        ),
    ),
    (
        frappe_handlers,
        handlers_source,
        "const pendingNativeTicketRooms = new Map();",
    ),
    (
        frappe_handlers,
        handlers_source,
        (
            "if (pendingNativeTicketRooms.get(room) !== token) return;\n"
            "                   pendingNativeTicketRooms.delete(room);\n"
            "                   if (socket.connected !== true) return;"
        ),
    ),
    (
        frappe_handlers,
        handlers_source,
        (
            'if (doctype === "HD Ticket") '
            'pendingNativeTicketRooms.delete(doc_room(doctype, docname));'
        ),
    ),
    (
        frappe_handlers,
        handlers_source,
        "pendingNativeTicketRooms.clear();",
    ),
    (
        frappe_handlers,
        handlers_source,
        (
            'const nativeTicketRoom = doctype === "HD Ticket"\n'
            '\t\t\t? open_doc_room(doctype, docname)\n'
            '\t\t\t: null;'
        ),
    ),
    (
        frappe_handlers,
        handlers_source,
        (
            'if (pendingNativeTicketRooms.get(nativeTicketRoom) !== nativeTicketToken) return;\n'
            '\t\t\t\t\tpendingNativeTicketRooms.delete(nativeTicketRoom);\n'
            '\t\t\t\t\tif (socket.connected !== true) return;'
        ),
    ),
    (
        frappe_handlers,
        handlers_source,
        (
            'socket.on("doc_close", function (doctype, docname) {\n'
            '\t\tif (doctype === "HD Ticket") pendingNativeTicketRooms.delete(open_doc_room(doctype, docname));'
        ),
    ),
    (
        frappe_handlers,
        handlers_source,
        "args.onComplete(allowed);",
    ),
    (
        frappe_handlers,
        handlers_source,
        (
            'onComplete: () => {\n'
            '                   if (pendingNativeTicketRooms.get(room) === token) {'
        ),
    ),
    (
        frappe_handlers,
        handlers_source,
        (
            'if (nativeTicketRoom && pendingNativeTicketRooms.get(nativeTicketRoom) === nativeTicketToken) {\n'
            '\t\t\t\t\tpendingNativeTicketRooms.delete(nativeTicketRoom);'
        ),
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

for forbidden in (
    'socket.on("notify_ticket_update"',
    '.emit("ticket_update"',
):
    if forbidden in helpdesk_source:
        raise RuntimeError(
            {
                "path": str(helpdesk_handlers),
                "forbidden_source": forbidden,
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

frappe_handlers.write_text(
    handlers_source,
    encoding="utf-8",
)

helpdesk_handlers.write_text(
    helpdesk_source,
    encoding="utf-8",
)

for path in (
    frappe_utils,
    frappe_authenticate,
    frappe_index,
    frappe_handlers,
    helpdesk_handlers,
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
