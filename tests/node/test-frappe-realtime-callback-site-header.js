const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const filename = process.argv[2];

assert.ok(
  filename,
  "Generated Frappe realtime utils.js filename is required"
);

const source = fs.readFileSync(filename, "utf8");

const endpoint =
  "/api/method/telephony.realtime_ticket_authorization" +
  ".require_ticket_realtime_access";

function createHarness() {
  const requests = [];

  const superagent = {
    get(url) {
      const request = {
        url,
        headers: {},
        queryParams: null,

        set(name, value) {
          this.headers[name] = value;
          return this;
        },

        query(params) {
          this.queryParams = params;
          return this;
        },
      };

      requests.push(request);
      return request;
    },
  };

  const sandbox = {
    module: { exports: {} },
    URL,

    require(name) {
      if (name === "superagent") {
        return superagent;
      }

      if (name === "../node_utils") {
        return {
          get_conf() {
            return {
              webserver_host: "backend",
              webserver_port: 8000,
            };
          },
        };
      }

      throw new Error(`Unexpected dependency: ${name}`);
    },
  };

  vm.runInNewContext(source, sandbox, { filename });

  return {
    frappe_request: sandbox.module.exports.frappe_request,
    requests,
  };
}

function makeSocket(overrides = {}) {
  return {
    site_name: "frontend",
    sid: "test-session",
    authorization_header: undefined,
    request: {
      headers: {
        origin: "http://localhost:8080",
      },
    },
    ...overrides,
  };
}

let passed = 0;

// Session authentication must preserve the SID and forward the site.
{
  const { frappe_request, requests } = createHarness();

  const result = frappe_request(endpoint, makeSocket());

  assert.equal(requests.length, 1);
  assert.equal(result, requests[0]);

  assert.equal(
    result.url,
    `http://backend:8000${endpoint}`
  );

  assert.equal(
    result.headers["X-Frappe-Site-Name"],
    "frontend"
  );

  assert.equal(result.queryParams.sid, "test-session");
  assert.equal(result.headers.Authorization, undefined);

  passed++;
  console.log("CALLBACK_SESSION_SITE_HEADER=PASS");
}

// Token authentication must preserve the token and forward the site.
{
  const { frappe_request, requests } = createHarness();

  const result = frappe_request(
    endpoint,
    makeSocket({
      authorization_header: "token test-key:test-secret",
    })
  );

  assert.equal(requests.length, 1);

  assert.equal(
    result.headers["X-Frappe-Site-Name"],
    "frontend"
  );

  assert.equal(
    result.headers.Authorization,
    "token test-key:test-secret"
  );

  assert.equal(result.queryParams, null);

  passed++;
  console.log("CALLBACK_TOKEN_SITE_HEADER=PASS");
}

// Missing or invalid authenticated site identity must fail closed.
for (const site_name of [undefined, "", "   ", null, 123]) {
  const { frappe_request, requests } = createHarness();

  assert.throws(
    () => frappe_request(
      endpoint,
      makeSocket({ site_name })
    ),
    /Missing authenticated Frappe site/
  );

  assert.equal(
    requests.length,
    0,
    "Invalid site identity must not issue an HTTP request"
  );

  passed++;
}

console.log("CALLBACK_MISSING_SITE_FAIL_CLOSED=PASS");

// A missing socket must also fail before issuing a request.
{
  const { frappe_request, requests } = createHarness();

  assert.throws(
    () => frappe_request(endpoint, undefined),
    /Missing authenticated Frappe site/
  );

  assert.equal(requests.length, 0);

  passed++;
  console.log("CALLBACK_MISSING_SOCKET_FAIL_CLOSED=PASS");
}

assert.equal(passed, 8);

console.log(
  `FRAPPE_REALTIME_CALLBACK_SITE_HEADER_TESTS=${passed}/8 PASS`
);
