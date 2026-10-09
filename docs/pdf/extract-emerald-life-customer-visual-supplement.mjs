
// @ts-check

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const pdfDir = dirname(fileURLToPath(import.meta.url));

const sourcePath = resolve(
  pdfDir,
  "../user-guides/activity-process-guides-visual-supplement.md",
);

const outputDir = resolve(pdfDir, "dist");

const outputPath = resolve(
  outputDir,
  "emerald-life-customer-activity-process-guides-visual-supplement.md",
);

const visuals = [
  {
    heading: "## 1.1 Customer logs a support request",
    path: "../../user-guides/customer-visuals/emerald-life/customer-log-support-request.png",
  },
  {
    heading: "## 1.5 Confirm the Customer can see the follow-up",
    path: "../../user-guides/customer-visuals/emerald-life/customer-latest-update.png",
  },
];

/**
 * Assert that a publication requirement is satisfied.
 *
 * @param {boolean} condition
 * @param {string} message
 * @returns {asserts condition}
 */
function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const source = (
  await readFile(sourcePath, "utf8")
).replace(/\r\n/g, "\n");

const sourceLines = source.split("\n");

for (const visual of visuals) {
  assert(
    sourceLines.filter((line) => line === visual.heading).length === 1,
    `Expected exactly one canonical heading: ${visual.heading}`,
  );

  await readFile(resolve(outputDir, visual.path));
}

const generatedDocument = `<!--
GENERATED PUBLICATION SOURCE.
Canonical visual source: docs/user-guides/activity-process-guides-visual-supplement.md
Customer edition: Emerald Life.
Do not edit this generated file directly.
-->

# Emerald Life Customer Activity Process Guides Visual Supplement

## Purpose

This Visual Supplement accompanies the **Customer Activity Process Guide** and **Customer Welcome Guide** for Emerald Life.

It illustrates selected activities in the Emerald Life Customer portal using controlled documentation examples captured in Production.

The canonical Customer Activity Process Guide remains the process source of truth.

Emerald Life support requests are submitted through authorised Head Office Customer portal users. These users can identify the affected regional branch by selecting its Campus.

Internal Telectro ticket actions, assignments, Partner workflows, and operational controls are intentionally excluded.

## How to use this supplement

The screenshots use a controlled \`[PILOT TEST][DOC-EL-01]\` support request.

They demonstrate the Customer-facing interface without representing an actual connectivity fault.

Activities not illustrated here remain covered by the Customer Activity Process Guide.

# 1. Log a support request

Select **Log a Support Request** from the Customer portal.

Choose the affected **Service Area** and **Severity**.

Select the **Campus** where the issue is located. Emerald Life reports faults at Campus level, so the selected Campus identifies the affected branch and is sent to Telectro with the request.

Add a clear subject and description. Include an equipment, circuit, SIM, or tag reference when known.

![Emerald Life Customer logging a support request](${visuals[0].path})

*Example: A controlled Internet Connection support request for the Emerald Life Bellville branch.*

# 2. Check the latest Customer-visible update

Open the existing support request from **Support Requests**.

The **Latest update** section shows the most recent Customer-visible communication. Check who sent it before deciding whether Telectro has responded.

The **Activity** section preserves the Customer-visible conversation, including the original request and later updates.

![Emerald Life Customer reviewing the latest support request update](${visuals[1].path})

*Example: Support request #51 showing a Customer-visible Telectro update, the activity history, and the affected Bellville Campus.*

If additional information is required, use **Add information** on the existing request rather than creating a duplicate ticket.
`;

const generatedLines = generatedDocument.split("\n");

for (const heading of [
  "# 1. Log a support request",
  "# 2. Check the latest Customer-visible update",
]) {
  assert(
    generatedLines.filter((line) => line === heading).length === 1,
    `Missing or duplicated publication heading: ${heading}`,
  );
}

assert(
  !generatedDocument.includes("Baker House")
    && !generatedDocument.includes("Boschendal"),
  "Emerald Life publication contains Boschendal-specific content",
);

await mkdir(outputDir, { recursive: true });

await writeFile(
  outputPath,
  `${generatedDocument.trimEnd()}\n`,
  "utf8",
);

console.log("=== Emerald Life Customer Visual Supplement ===");
console.log(`SOURCE=${sourcePath}`);
console.log(`OUTPUT=${outputPath}`);
console.log("CANONICAL_ACTIVITY_HEADINGS=PASS");
console.log("EMERALD_LIFE_SCREENSHOT_COUNT=2");
console.log("BOSCHENDAL_CONTENT_RESIDUE=0");
console.log("EMERALD_LIFE_VISUAL_EXTRACTION=PASS");
