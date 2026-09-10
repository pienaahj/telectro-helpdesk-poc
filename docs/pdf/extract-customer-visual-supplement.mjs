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
  "customer-activity-process-guides-visual-supplement.md",
);

/*
 * The Customer Visual Supplement is intentionally selective.
 *
 * It does not reproduce the complete Master Customer chapter because several
 * Master screenshots show internal Telectro controls that Customer users do
 * not see.
 *
 * Customer publication visuals:
 *
 *   Master 1.1 -> Customer 1
 *   Master 1.5 -> Customer 2
 *
 * The extractor proves that each selected image/caption pair still exists
 * exactly once in the Master before generating the audience edition.
 */
const selectedVisuals = [
  {
    sourceHeading: "## 1.1 Customer logs a support request",
    closingBoundary:
      "## 1.2 Attach ticket evidence before making it Customer-visible",
    image:
      "![Customer logging a support request](activity-process-guides-visuals/visual-27-customer-log-support-request.png)",
    caption:
      "*The Customer request form with Boschendal location context and the selected `Buildings: Baker House` Fault Point.*",
  },
  {
    sourceHeading:
      "## 1.5 Confirm the Customer can see the follow-up",
    closingBoundary:
      "## 1.6 Select completion evidence when resolving",
    image:
      "![Customer follow-up visible on ticket](activity-process-guides-visuals/visual-05-customer-follow-up-visible-on-ticket.png)",
    caption:
      "*The Customer sees the Telectro update on the correct support request together with the ticket's current context.*",
  },
];

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

function publicationImagePath(imageLine) {
  const sourcePrefix =
    "(activity-process-guides-visuals/";

  const publicationPrefix =
    "(../../user-guides/activity-process-guides-visuals/";

  if (!imageLine.includes(sourcePrefix)) {
    fail(
      `Expected Master visual path prefix in "${imageLine}".`,
    );
  }

  return imageLine.replace(
    sourcePrefix,
    publicationPrefix,
  );
}

function assertOrderedIndexes(items) {
  for (let index = 0; index < items.length - 1; index += 1) {
    if (items[index].index >= items[index + 1].index) {
      fail(
        `Expected "${items[index].label}" to appear before "${items[index + 1].label}".`,
      );
    }
  }
}

const rawSource = await readFile(sourcePath, "utf8");

const source = rawSource.replace(/\r\n/g, "\n");
const sourceLines = source.split("\n");

const masterHeading =
  "# Activity Process Guides Visual Supplement";

const customerChapterHeading =
  "# 1. Customer requests, Customer-visible updates, and evidence";

const ownershipChapterHeading =
  "# 2. Ticket ownership and internal collaboration";

findUniqueLine(sourceLines, masterHeading);

const customerChapterIndex = findUniqueLine(
  sourceLines,
  customerChapterHeading,
);

const ownershipChapterIndex = findUniqueLine(
  sourceLines,
  ownershipChapterHeading,
);

if (customerChapterIndex >= ownershipChapterIndex) {
  fail(
    "Master Customer chapter must appear before the ownership chapter.",
  );
}

/*
 * Prove every selected visual remains inside the Master Customer chapter
 * and that its heading, image, and caption occur in the expected order.
 */
for (const visual of selectedVisuals) {
  const headingIndex = findUniqueLine(
    sourceLines,
    visual.sourceHeading,
  );

  const imageIndex = findUniqueLine(
    sourceLines,
    visual.image,
  );

  const captionIndex = findUniqueLine(
    sourceLines,
    visual.caption,
  );

const closingBoundaryIndex = findUniqueLine(
    sourceLines,
    visual.closingBoundary,
  );

  assertOrderedIndexes([
    {
      label: visual.sourceHeading,
      index: headingIndex,
    },
    {
      label: visual.image,
      index: imageIndex,
    },
    {
      label: visual.caption,
      index: captionIndex,
    },
    {
      label: visual.closingBoundary,
      index: closingBoundaryIndex,
    },
  ]);

  if (
    headingIndex <= customerChapterIndex
    || captionIndex >= ownershipChapterIndex
  ) {
    fail(
      `Selected Customer visual "${visual.image}" is outside the expected Master Customer chapter.`,
    );
  }
}

const customerRequestVisual = selectedVisuals[0];
const customerUpdateVisual = selectedVisuals[1];
const customerRequestPublicationImage =
  publicationImagePath(customerRequestVisual.image);

const customerUpdatePublicationImage =
  publicationImagePath(customerUpdateVisual.image);

const generatedDocument = `<!--
GENERATED PUBLICATION SOURCE.
Canonical visual source: docs/user-guides/activity-process-guides-visual-supplement.md
Derived scope: selected Customer-facing visuals from the Master Visual Supplement.
Do not edit this generated file directly.
-->

# Customer Activity Process Guides Visual Supplement

## Purpose

This Customer Visual Supplement is the Customer-facing audience edition derived from the **Activity Process Guides Visual Supplement**.

The canonical **Customer Activity Process Guide** remains the process source of truth. This supplement is intentionally selective: it shows only Customer-safe screens where visual recognition materially helps the Customer understand the portal.

Use this supplement together with:

- the Customer Activity Process Guide;
- the Customer Welcome Guide;
- the Boschendal Customer portal.

Internal Telectro ticket actions, evidence-management dialogs, assignment controls, Partner workflows, and operational queues are intentionally excluded from this Customer edition.

## How to use this supplement

The screenshots use controlled \`[PILOT TEST][DOC-NN]\` records captured in Production so that the examples match the real pilot UI while remaining clearly separate from live Customer work.

Activities that do not need a screenshot remain covered by the canonical Customer Activity Process Guide. This supplement does not attempt to reproduce every process step visually.

# 1. Log a support request

A Customer can log a new support request from the Customer portal and provide the affected service area, severity, location context, subject, and explanation.

Where a Boschendal location is known, selecting the closest relevant Fault Point helps make the affected place explicit.

${customerRequestPublicationImage}

${customerRequestVisual.caption}

# 2. Check the latest Customer-visible update

The Customer ticket page shows Customer-visible progress from Telectro without exposing internal Telectro notes, assignment activity, Partner review detail, or other internal operational information.

The latest update is shown prominently and remains part of the Customer-visible ticket history.

${customerUpdatePublicationImage}

*The Customer sees the latest Telectro update on the correct support request together with the ticket's current Customer-visible context.*

The same ticket page is the Customer's reference point when checking progress before deciding whether more information needs to be added to the existing request.
`;

const generatedLines =
  generatedDocument.replace(/\r\n/g, "\n").split("\n");

const expectedPublicationHeadings = [
  "# 1. Log a support request",
  "# 2. Check the latest Customer-visible update",
];

for (const heading of expectedPublicationHeadings) {
  if (countExactLine(generatedLines, heading) !== 1) {
    fail(
      `Generated Customer Visual Supplement heading is missing or duplicated: "${heading}".`,
    );
  }
}

const generatedNumberedHeadings =
  generatedLines.filter(
    (line) => /^# [1-2]\. /.test(line),
  );

if (generatedNumberedHeadings.length !== 2) {
  fail(
    `Expected 2 generated Customer visual chapters, found ${generatedNumberedHeadings.length}.`,
  );
}

const publicationImages = [
  customerRequestPublicationImage,
  customerUpdatePublicationImage,
];

for (const image of publicationImages) {
  if (!generatedDocument.includes(image)) {
    fail(
      `Generated Customer Visual Supplement is missing publication image "${image}".`,
    );
  }
}

const forbiddenImages = [
  "visual-01-ticket-evidence-upload-dialog.png",
  "visual-02-select-customer-visible-completion-evidence.png",
  "visual-03-customer-visible-update-action.png",
  "visual-04-customer-add-information.png",
];

for (const forbiddenImage of forbiddenImages) {
  if (generatedDocument.includes(forbiddenImage)) {
    fail(
      `Generated Customer Visual Supplement contains internal Telectro visual "${forbiddenImage}".`,
    );
  }
}

await mkdir(outputDir, {
  recursive: true,
});

await writeFile(
  outputPath,
  `${generatedDocument.trimEnd()}\n`,
  "utf8",
);

console.log(
  "=== Customer Visual Supplement extraction ===",
);

console.log(`SOURCE=${sourcePath}`);
console.log(`OUTPUT=${outputPath}`);
console.log("MASTER_CUSTOMER_CHAPTER_BOUNDARY=PASS");
console.log("SELECTED_CUSTOMER_VISUAL_COUNT=2");
console.log("VISUAL_27_SOURCE_PARITY=PASS");
console.log("VISUAL_05_SOURCE_PARITY=PASS");
console.log("INTERNAL_TELECTRO_VISUAL_RESIDUE=0");
console.log("CUSTOMER_VISUAL_CHAPTER_COUNT=2");
console.log("CUSTOMER_VISUAL_SUPPLEMENT_EXTRACTION=PASS");
