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
  "partner-activity-process-guide.md",
);

/*
 * Publication order is intentionally different from canonical numbering.
 *
 * Partner publication:
 *
 *   Canonical 21 -> Partner 1
 *   Canonical 10 -> Partner 2
 *   Canonical 11 -> Partner 3
 *
 * This presents the Partner workflows in operational order:
 *
 *   create Partner-originated request
 *   -> respond to Partner acceptance
 *
 *   separately:
 *
 *   Telectro assigns Partner work
 *   -> Partner submits work done
 */
const activities = [
  {
    canonicalNumber: 21,
    publicationNumber: 1,
    title: "Partner logs a Partner-originated service request",
    closingBoundary:
      "# 22. Activity Process Guide backlog",
  },
  {
    canonicalNumber: 10,
    publicationNumber: 2,
    title: "Partner responds to an acceptance request",
    closingBoundary:
      "# 11. Partner submits work done",
  },
  {
    canonicalNumber: 11,
    publicationNumber: 3,
    title: "Partner submits work done",
    closingBoundary:
      "# 12. Review Partner acceptance",
  },
];

const forbiddenBoundaryHeadings = [
  "# 12. Review Partner acceptance",
  "# 22. Activity Process Guide backlog",
];

const frontMatter = `<!--
GENERATED PUBLICATION SOURCE.
Canonical source: docs/user-guides/activity-process-guides.md
Derived scope: canonical Activities 21, 10, and 11.
Publication order: canonical 21 -> 1, canonical 10 -> 2, canonical 11 -> 3.
Do not edit the generated activity text directly.
-->

# ERPNext / Helpdesk Pilot Partner Activity Process Guide

## Purpose

This guide provides practical step-by-step instructions for Partner users working with Telectro through the Partner workspace.

It complements the Partner Welcome Guide. The Welcome Guide explains where Partner users start, the Partner organisation and membership model, and the boundaries of Partner access; this guide explains how to carry out the main Partner activities.

## What this guide covers

This guide explains how to:

* log a Partner-originated service request for Telectro;
* respond when Telectro requests Partner acceptance;
* submit completed work when Telectro has assigned fulfilment work to the Partner.

## Important Partner workflow boundary

The Partner workflow contains two separate process trains.

### Partner-originated request / Partner Acceptance

In this train:

\`\`\`text
Partner logs request
→ Request Source = Partner
→ Telectro fulfils the request
→ Telectro requests Partner acceptance
→ Partner accepts or requests rework
→ Telectro reviews and finalises
\`\`\`

### Telectro-assigned Partner work / Partner Work Completion

In this train:

\`\`\`text
Telectro assigns fulfilment work to Partner
→ Partner performs the work
→ Partner submits work done
→ Telectro reviews the completed work
→ Telectro accepts, requests rework, resolves, or closes as appropriate
\`\`\`

Partner Acceptance and Partner Work Completion are separate workflows and should not be treated as the same process.

## Partner organisation

Partner access operates through the Partner organisation represented by the authenticated Partner user.

A Partner user may act only within the Partner organisation scope permitted by their enabled membership.

## How this guide is maintained

The activity instructions in this Partner guide are derived from the canonical ERPNext / Helpdesk Pilot Activity Process Guides.

Partner-facing editions are regenerated from that canonical source rather than maintained as separate process manuals.

---
`;

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

function numberedActivityReferences(value) {
  return value.match(/\bActivity\s+\d+\b/g) || [];
}

const rawSource = await readFile(sourcePath, "utf8");

const source = rawSource.replace(/\r\n/g, "\n");
const sourceLines = source.split("\n");

const canonicalSections = new Map();

for (const activity of activities) {
  const canonicalHeading =
    `# ${activity.canonicalNumber}. ${activity.title}`;

  const startIndex = findUniqueLine(
    sourceLines,
    canonicalHeading,
  );

  const endIndex = findUniqueLine(
    sourceLines,
    activity.closingBoundary,
  );

  if (startIndex >= endIndex) {
    fail(
      `Canonical Activity ${activity.canonicalNumber}: heading must appear before boundary "${activity.closingBoundary}".`,
    );
  }

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

  const canonicalBody =
    canonicalBodyLines.join("\n");

  const numberedReferences =
    numberedActivityReferences(canonicalBody);

  if (numberedReferences.length) {
    fail(
      `Canonical Activity ${activity.canonicalNumber}: unexpected numbered activity reference(s): ${numberedReferences.join(", ")}`,
    );
  }

  canonicalSections.set(
    activity.canonicalNumber,
    canonicalBody,
  );
}

/*
 * Prove the two contiguous canonical Partner sections have the expected
 * source relationship independently of publication order.
 */
const canonical10Index = findUniqueLine(
  sourceLines,
  "# 10. Partner responds to an acceptance request",
);

const canonical11Index = findUniqueLine(
  sourceLines,
  "# 11. Partner submits work done",
);

const canonical12Index = findUniqueLine(
  sourceLines,
  "# 12. Review Partner acceptance",
);

if (
  !(
    canonical10Index < canonical11Index
    && canonical11Index < canonical12Index
  )
) {
  fail(
    "Canonical Partner Activities 10 and 11 do not have the expected source order.",
  );
}

/*
 * Prove canonical Activity 21 retains its expected closing boundary.
 */
const canonical21Index = findUniqueLine(
  sourceLines,
  "# 21. Partner logs a Partner-originated service request",
);

const canonical22Index = findUniqueLine(
  sourceLines,
  "# 22. Activity Process Guide backlog",
);

if (canonical21Index >= canonical22Index) {
  fail(
    "Canonical Activity 21 must appear before Activity 22.",
  );
}

const generatedSections = [];

for (const activity of activities) {
  const canonicalBody =
    canonicalSections.get(activity.canonicalNumber);

  if (typeof canonicalBody !== "string") {
    fail(
      `Canonical body missing for Activity ${activity.canonicalNumber}.`,
    );
  }

  const publicationHeading =
    `# ${activity.publicationNumber}. ${activity.title}`;

  generatedSections.push(
    `${publicationHeading}\n${canonicalBody}`,
  );
}

const generatedDocument =
  `${frontMatter.trimEnd()}\n\n`
  + `${generatedSections.join("\n\n")}\n`;

const generatedLines =
  generatedDocument.split("\n");

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
    (line) => /^# [1-3]\. /.test(line),
  );

if (generatedNumberedHeadings.length !== 3) {
  fail(
    `Expected 3 generated numbered activities, found ${generatedNumberedHeadings.length}.`,
  );
}

if (generatedDocument.includes("## Related docs")) {
  fail(
    'Generated Partner guide still contains "## Related docs".',
  );
}

for (const forbiddenHeading of forbiddenBoundaryHeadings) {
  if (generatedDocument.includes(forbiddenHeading)) {
    fail(
      `Generated Partner guide contains forbidden canonical boundary "${forbiddenHeading}".`,
    );
  }
}

const generatedNumberedReferences =
  numberedActivityReferences(generatedDocument);

if (generatedNumberedReferences.length) {
  fail(
    `Generated Partner guide contains stale numbered activity reference(s): ${generatedNumberedReferences.join(", ")}`,
  );
}

/*
 * Final body-parity proof:
 *
 * generated publication body
 * =
 * canonical body
 *
 * No Partner publication-only body transforms are permitted.
 */
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

  const canonicalBody =
    canonicalSections.get(activity.canonicalNumber);

  if (generatedBody !== canonicalBody) {
    fail(
      `Body parity failed for canonical Activity ${activity.canonicalNumber} → Partner Activity ${activity.publicationNumber}.`,
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
  "=== Partner Activity Process Guide extraction ===",
);

console.log(`SOURCE=${sourcePath}`);
console.log(`OUTPUT=${outputPath}`);

console.log(
  "CANONICAL_EXTRACTION_ORDER=21_10_11",
);

console.log(
  "PARTNER_ACTIVITY_COUNT=3",
);

console.log(
  "PARTNER_ACTIVITY_NUMBERING=1_TO_3",
);

console.log(
  "RELATED_DOCS_RESIDUE=0",
);

console.log(
  "TELECTRO_ACTIVITY_12_RESIDUE=0",
);

console.log(
  "BACKLOG_ACTIVITY_22_RESIDUE=0",
);

console.log(
  "NUMBERED_ACTIVITY_REFERENCE_RESIDUE=0",
);

for (const activity of activities) {
  const canonicalBody =
    canonicalSections.get(activity.canonicalNumber);

  if (typeof canonicalBody !== "string") {
    fail(
      `Canonical body missing for Activity ${activity.canonicalNumber}.`,
    );
  }

  console.log(
    `BODY_PARITY_${activity.canonicalNumber}_TO_${activity.publicationNumber}=PASS`,
  );

  console.log(
    `BODY_SHA256_${activity.canonicalNumber}_TO_${activity.publicationNumber}=${sha256(canonicalBody)}`,
  );
}

console.log(
  "PARTNER_ACTIVITY_GUIDE_NO_BODY_TRANSFORMS=PASS",
);

console.log(
  "PARTNER_ACTIVITY_GUIDE_EXTRACTION=PASS",
);
