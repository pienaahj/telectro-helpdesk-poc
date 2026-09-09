// @ts-check

import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const pdfDir = dirname(fileURLToPath(import.meta.url));

const sourcePath = resolve(
  pdfDir,
  "../user-guides/activity-process-guides.md",
);

const outputDir = resolve(pdfDir, "dist");

const outputPath = resolve(
  outputDir,
  "customer-activity-process-guide.md",
);

const activities = [
  {
    canonicalNumber: 5,
    publicationNumber: 1,
    title: "Customer logs a support request",
  },
  {
    canonicalNumber: 6,
    publicationNumber: 2,
    title: "Customer adds follow-up information",
  },
  {
    canonicalNumber: 7,
    publicationNumber: 3,
    title: "Customer views latest update",
  },
  {
    canonicalNumber: 8,
    publicationNumber: 4,
    title: "Customer downloads Customer-visible evidence",
  },
  {
    canonicalNumber: 9,
    publicationNumber: 5,
    title: "Customer checks resolved ticket outcome",
  },
];

const closingBoundary =
  "# 10. Partner responds to an acceptance request";

const frontMatter = `<!--
GENERATED PUBLICATION SOURCE.
Canonical source: docs/user-guides/activity-process-guides.md
Derived scope: canonical Activities 5–9.
Do not edit the generated activity text directly.
-->

# ERPNext / Helpdesk Pilot Customer Activity Process Guide

## Purpose

This guide provides practical step-by-step instructions for Customer users working with support requests in the Customer portal.

It complements the Customer Welcome Guide. The Welcome Guide explains where to start and what the Customer portal is for; this guide explains how to carry out the main Customer support activities.

## What this guide covers

This guide explains how to:

* log a new support request;
* add follow-up information to an existing request;
* check the latest Customer-visible update;
* open or download Customer-visible evidence;
* review the outcome of a resolved request.

## Important Customer workflow boundary

The Customer portal is not a formal approval, rejection, sign-off, or closure workflow.

Telectro manages ticket resolution and closure.

If something still needs attention, use \`Add information\` on the existing support request where appropriate.

If the issue is genuinely new or materially different, log a new support request.

## How this guide is maintained

The activity instructions in this Customer guide are derived from the canonical ERPNext / Helpdesk Pilot Activity Process Guides.

Customer-facing editions are regenerated from that canonical source rather than maintained as separate process manuals.

---
`;

const activity6CanonicalReference =
  "This is different from the Telectro Customer-visible evidence workflow in Activity 1, where Telectro first attaches evidence to the HD Ticket and then deliberately selects that existing file for Customer visibility.";

const activity6CustomerReference =
  "This is different from Telectro's Customer-visible evidence workflow, where Telectro first attaches evidence to the HD Ticket and then deliberately selects that existing file for Customer visibility.";

function fail(message) {
  throw new Error(message);
}

function countExactLine(lines, expected) {
  return lines.filter((line) => line === expected).length;
}

function findUniqueLine(lines, expected) {
  const count = countExactLine(lines, expected);

  if (count !== 1) {
    fail(
      `Expected exactly one line "${expected}", found ${count}.`,
    );
  }

  return lines.findIndex((line) => line === expected);
}

function trimTrailingBlankLines(lines) {
  const result = [...lines];

  while (
    result.length
    && result[result.length - 1].trim() === ""
  ) {
    result.pop();
  }

  return result;
}

function sha256(value) {
  return createHash("sha256")
    .update(value, "utf8")
    .digest("hex");
}

function replaceExactlyOnce(
  value,
  expected,
  replacement,
  label,
) {
  const first = value.indexOf(expected);
  const last = value.lastIndexOf(expected);

  if (first === -1) {
    fail(
      `${label}: expected publication transform text was not found.`,
    );
  }

  if (first !== last) {
    fail(
      `${label}: expected publication transform text occurred more than once.`,
    );
  }

  return value.replace(expected, replacement);
}

function numberedActivityReferences(value) {
  return value.match(/\bActivity\s+\d+\b/g) || [];
}

const rawSource = await readFile(sourcePath, "utf8");

const source = rawSource.replace(/\r\n/g, "\n");
const sourceLines = source.split("\n");

const canonicalHeadingIndexes = activities.map(
  ({ canonicalNumber, title }) => {
    const heading = `# ${canonicalNumber}. ${title}`;

    return {
      heading,
      index: findUniqueLine(sourceLines, heading),
    };
  },
);

const boundaryIndex = findUniqueLine(
  sourceLines,
  closingBoundary,
);

for (
  let index = 0;
  index < canonicalHeadingIndexes.length - 1;
  index += 1
) {
  const current = canonicalHeadingIndexes[index];
  const next = canonicalHeadingIndexes[index + 1];

  if (current.index >= next.index) {
    fail(
      `Canonical activity order is invalid: "${current.heading}" must appear before "${next.heading}".`,
    );
  }
}

if (
  canonicalHeadingIndexes[
    canonicalHeadingIndexes.length - 1
  ].index >= boundaryIndex
) {
  fail(
    `Canonical Activity 9 must appear before "${closingBoundary}".`,
  );
}

const generatedSections = [];
const canonicalBodies = new Map();
const expectedGeneratedBodies = new Map();

for (let index = 0; index < activities.length; index += 1) {
  const activity = activities[index];

  const startIndex =
    canonicalHeadingIndexes[index].index;

  const endIndex =
    index < activities.length - 1
      ? canonicalHeadingIndexes[index + 1].index
      : boundaryIndex;

  const canonicalSection = sourceLines.slice(
    startIndex,
    endIndex,
  );

  const relatedDocsIndexes = canonicalSection
    .map((line, lineIndex) => ({
      line,
      lineIndex,
    }))
    .filter(({ line }) => line === "## Related docs")
    .map(({ lineIndex }) => lineIndex);

  if (relatedDocsIndexes.length !== 1) {
    fail(
      `Canonical Activity ${activity.canonicalNumber}: expected exactly one "## Related docs" section, found ${relatedDocsIndexes.length}.`,
    );
  }

  const relatedDocsIndex = relatedDocsIndexes[0];

  const canonicalBodyLines = trimTrailingBlankLines(
    canonicalSection.slice(
      1,
      relatedDocsIndex,
    ),
  );

  const canonicalBody = canonicalBodyLines.join("\n");

  canonicalBodies.set(
    activity.canonicalNumber,
    canonicalBody,
  );

  let publicationBody = canonicalBody;

  if (activity.canonicalNumber === 6) {
    publicationBody = replaceExactlyOnce(
      publicationBody,
      activity6CanonicalReference,
      activity6CustomerReference,
      "Canonical Activity 6",
    );
  } else {
    const numberedReferences =
      numberedActivityReferences(publicationBody);

    if (numberedReferences.length) {
      fail(
        `Canonical Activity ${activity.canonicalNumber}: unexpected numbered activity reference(s): ${numberedReferences.join(", ")}`,
      );
    }
  }

  expectedGeneratedBodies.set(
    activity.publicationNumber,
    publicationBody,
  );

  const publicationHeading =
    `# ${activity.publicationNumber}. ${activity.title}`;

  generatedSections.push(
    `${publicationHeading}\n${publicationBody}`,
  );
}

const generatedDocument =
  `${frontMatter.trimEnd()}\n\n`
  + `${generatedSections.join("\n\n")}\n`;

const generatedLines = generatedDocument.split("\n");

for (const activity of activities) {
  const publicationHeading =
    `# ${activity.publicationNumber}. ${activity.title}`;

  if (
    countExactLine(
      generatedLines,
      publicationHeading,
    ) !== 1
  ) {
    fail(
      `Generated publication heading is missing or duplicated: "${publicationHeading}".`,
    );
  }
}

const generatedNumberedHeadings =
  generatedLines.filter(
    (line) => /^# [1-5]\. /.test(line),
  );

if (generatedNumberedHeadings.length !== 5) {
  fail(
    `Expected 5 generated numbered activities, found ${generatedNumberedHeadings.length}.`,
  );
}

if (generatedDocument.includes("## Related docs")) {
  fail(
    'Generated Customer guide still contains "## Related docs".',
  );
}

if (generatedDocument.includes(closingBoundary)) {
  fail(
    "Generated Customer guide contains canonical Activity 10.",
  );
}

const generatedNumberedReferences =
  numberedActivityReferences(generatedDocument);

if (generatedNumberedReferences.length) {
  fail(
    `Generated Customer guide contains stale numbered activity reference(s): ${generatedNumberedReferences.join(", ")}`,
  );
}

for (let index = 0; index < activities.length; index += 1) {
  const activity = activities[index];

  const publicationHeading =
    `# ${activity.publicationNumber}. ${activity.title}`;

  const startIndex = findUniqueLine(
    generatedLines,
    publicationHeading,
  );

  let endIndex = generatedLines.length;

  if (index < activities.length - 1) {
    const nextActivity = activities[index + 1];

    endIndex = findUniqueLine(
      generatedLines,
      `# ${nextActivity.publicationNumber}. ${nextActivity.title}`,
    );
  }

  const generatedBody = trimTrailingBlankLines(
    generatedLines.slice(
      startIndex + 1,
      endIndex,
    ),
  ).join("\n");

  const expectedBody =
    expectedGeneratedBodies.get(
      activity.publicationNumber,
    );

  if (generatedBody !== expectedBody) {
    fail(
      `Body parity failed for canonical Activity ${activity.canonicalNumber} → Customer Activity ${activity.publicationNumber}.`,
    );
  }
}

await mkdir(outputDir, {
  recursive: true,
});

await writeFile(
  outputPath,
  generatedDocument,
  "utf8",
);

console.log(
  "=== Customer Activity Process Guide extraction ===",
);

console.log(`SOURCE=${sourcePath}`);
console.log(`OUTPUT=${outputPath}`);
console.log("CANONICAL_ACTIVITY_RANGE=5-9");
console.log("CUSTOMER_ACTIVITY_COUNT=5");
console.log("CUSTOMER_ACTIVITY_NUMBERING=1_TO_5");
console.log("RELATED_DOCS_RESIDUE=0");
console.log("PARTNER_ACTIVITY_10_RESIDUE=0");
console.log("NUMBERED_ACTIVITY_REFERENCE_RESIDUE=0");

for (const activity of activities) {
  const canonicalBody =
    canonicalBodies.get(activity.canonicalNumber);

  const generatedBody =
    expectedGeneratedBodies.get(
      activity.publicationNumber,
    );

  console.log(
    `BODY_PARITY_${activity.canonicalNumber}_TO_${activity.publicationNumber}=PASS`,
  );

  console.log(
    `BODY_SHA256_${activity.canonicalNumber}_TO_${activity.publicationNumber}=${sha256(generatedBody)}`,
  );

  if (
    activity.canonicalNumber !== 6
    && canonicalBody !== generatedBody
  ) {
    fail(
      `Unexpected body transform occurred for canonical Activity ${activity.canonicalNumber}.`,
    );
  }
}

console.log(
  "ACTIVITY_6_PUBLICATION_REFERENCE_NEUTRALIZATION=PASS",
);

console.log(
  "CUSTOMER_ACTIVITY_GUIDE_EXTRACTION=PASS",
);
