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
  "partner-activity-process-guides-visual-supplement.md",
);

/*
 * The Partner Visual Supplement is intentionally selective.
 *
 * Partner-facing publication scope:
 *
 *   Master 3.1 -> Partner-originated request creation
 *   Master 3.3 -> pending Partner Acceptance
 *   Master 3.4 -> Partner requests rework
 *   Master 3.5 -> renewed Partner Acceptance request
 *
 *   Master 4.2 -> Partner sees Partner Work rework
 *   Master 4.3 -> Partner resubmits corrected work
 *
 * Telectro-only review dialogs, queues, and internal final-review screens
 * remain in the Master Visual Supplement but are excluded here.
 */
const selectedVisuals = [
  {
    sourceHeading:
      "## 3.1 Partner logs a service request",
    closingBoundary:
      "## 3.2 Telectro requests Partner Acceptance",
    image:
      "![Partner logs service request](activity-process-guides-visuals/visual-28-partner-log-service-request.png)",
    caption:
      "*The request carries Partner organisation, Account, location, request type, subject, summary, and optional evidence context.*",
  },
  {
    sourceHeading:
      "## 3.1 Partner logs a service request",
    closingBoundary:
      "## 3.2 Telectro requests Partner Acceptance",
    image:
      "![Partner request created](activity-process-guides-visuals/visual-29-partner-request-created.png)",
    caption:
      "*The newly created Partner-originated ticket is visible with its Open status, request type, and Telectro fulfilment responsibility.*",
  },
  {
    sourceHeading:
      "## 3.3 Partner reviews the pending acceptance request",
    closingBoundary:
      "## 3.4 Partner requests rework when the outcome still needs correction",
    image:
      "![Partner Acceptance pending](activity-process-guides-visuals/visual-16-partner-acceptance-pending.png)",
    caption:
      "*The Partner-safe view shows the request context, the Partner Acceptance Requested note, and the two Partner response actions.*",
  },
  {
    sourceHeading:
      "## 3.4 Partner requests rework when the outcome still needs correction",
    closingBoundary:
      "## 3.5 Telectro requests acceptance again after correction",
    image:
      "![Partner Request Rework dialog](activity-process-guides-visuals/visual-17-partner-request-rework-dialog.png)",
    caption:
      "*The Partner gives a specific reason describing what still needs to be corrected.*",
  },
  {
    sourceHeading:
      "## 3.4 Partner requests rework when the outcome still needs correction",
    closingBoundary:
      "## 3.5 Telectro requests acceptance again after correction",
    image:
      "![Partner rework requested result](activity-process-guides-visuals/visual-18-partner-rework-requested-result.png)",
    caption:
      "*The ticket now shows `Rework Required` together with the reason and prior acceptance-request context.*",
  },
  {
    sourceHeading:
      "## 3.5 Telectro requests acceptance again after correction",
    closingBoundary:
      "# 4. Telectro-assigned Partner Work Completion and rework",
    image:
      "![Partner Acceptance requested again](activity-process-guides-visuals/visual-21-partner-acceptance-requested-again.png)",
    caption:
      "*The visible sequence shows why the request returned to the Partner and what Telectro changed before asking for acceptance again.*",
  },
  {
    sourceHeading:
      "## 4.2 Partner sees the rework requirement",
    closingBoundary:
      "## 4.3 Partner resubmits corrected work",
    image:
      "![Partner Work rework required](activity-process-guides-visuals/visual-24-partner-work-rework-required.png)",
    caption:
      "*The Partner can see exactly what must be corrected before submitting Work Done again.*",
  },
  {
    sourceHeading:
      "## 4.3 Partner resubmits corrected work",
    closingBoundary:
      "## 4.4 Telectro reviews the corrected Partner work",
    image:
      "![Partner Work resubmitted](activity-process-guides-visuals/visual-25-partner-work-resubmitted.png)",
    caption:
      "*The corrected submission addresses the rework reason while keeping the earlier rework history visible.*",
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

function assertOrderedIndexes(items) {
  for (let index = 0; index < items.length - 1; index += 1) {
    if (items[index].index >= items[index + 1].index) {
      fail(
        `Expected "${items[index].label}" to appear before "${items[index + 1].label}".`,
      );
    }
  }
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

const rawSource = await readFile(sourcePath, "utf8");

const source = rawSource.replace(/\r\n/g, "\n");
const sourceLines = source.split("\n");

const masterHeading =
  "# Activity Process Guides Visual Supplement";

const acceptanceChapterHeading =
  "# 3. Partner-originated requests and Partner Acceptance";

const partnerWorkChapterHeading =
  "# 4. Telectro-assigned Partner Work Completion and rework";

const maintenanceChapterHeading =
  "# 5. Publication and maintenance notes";

findUniqueLine(sourceLines, masterHeading);

const acceptanceChapterIndex = findUniqueLine(
  sourceLines,
  acceptanceChapterHeading,
);

const partnerWorkChapterIndex = findUniqueLine(
  sourceLines,
  partnerWorkChapterHeading,
);

const maintenanceChapterIndex = findUniqueLine(
  sourceLines,
  maintenanceChapterHeading,
);

assertOrderedIndexes([
  {
    label: acceptanceChapterHeading,
    index: acceptanceChapterIndex,
  },
  {
    label: partnerWorkChapterHeading,
    index: partnerWorkChapterIndex,
  },
  {
    label: maintenanceChapterHeading,
    index: maintenanceChapterIndex,
  },
]);

/*
 * Prove each selected image/caption pair still exists exactly once and
 * remains underneath its expected Master subsection.
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
    headingIndex <= acceptanceChapterIndex
    || captionIndex >= maintenanceChapterIndex
  ) {
    fail(
      `Selected Partner visual "${visual.image}" is outside the expected Master Partner chapters.`,
    );
  }
}

/*
 * Prove the selected visuals remain in the intended workflow train.
 */
for (const visual of selectedVisuals.slice(0, 6)) {
  const imageIndex = findUniqueLine(
    sourceLines,
    visual.image,
  );

  if (
    imageIndex <= acceptanceChapterIndex
    || imageIndex >= partnerWorkChapterIndex
  ) {
    fail(
      `Partner Acceptance visual "${visual.image}" is outside Master chapter 3.`,
    );
  }
}

for (const visual of selectedVisuals.slice(6)) {
  const imageIndex = findUniqueLine(
    sourceLines,
    visual.image,
  );

  if (
    imageIndex <= partnerWorkChapterIndex
    || imageIndex >= maintenanceChapterIndex
  ) {
    fail(
      `Partner Work visual "${visual.image}" is outside Master chapter 4.`,
    );
  }
}

const publicationImages =
  selectedVisuals.map(
    ({ image }) => publicationImagePath(image),
  );

const [
  partnerRequestImage,
  partnerRequestCreatedImage,
  acceptancePendingImage,
  acceptanceReworkDialogImage,
  acceptanceReworkResultImage,
  acceptanceAgainImage,
  partnerWorkReworkImage,
  partnerWorkResubmittedImage,
] = publicationImages;

const generatedDocument = `<!--
GENERATED PUBLICATION SOURCE.
Canonical visual source: docs/user-guides/activity-process-guides-visual-supplement.md
Derived scope: selected Partner-facing visuals from Master chapters 3 and 4.
Do not edit this generated file directly.
-->

# Partner Activity Process Guides Visual Supplement

## Purpose

This Partner Visual Supplement is the Partner-facing audience edition derived from the **Activity Process Guides Visual Supplement**.

The canonical **Partner Activity Process Guide** remains the process source of truth. This supplement is intentionally selective: it shows only Partner-safe screens where visual recognition materially helps a Partner understand the workflow.

Use this supplement together with:

- the Partner Activity Process Guide;
- the Partner Welcome Guide;
- the approved Partner Workspace and Partner-safe ticket pages.

Internal Telectro HD Ticket forms, Coordinator/Supervisor review dialogs, internal reports, and operational queues are intentionally excluded from this Partner edition.

## Two Partner workflow trains

There are two separate Partner workflows. They must not be confused.

### Partner asks Telectro to perform work

\`\`\`text
Partner logs request
→ Telectro performs the work
→ Telectro requests Partner Acceptance
→ Partner accepts or requests rework
→ Telectro reviews the Partner response
\`\`\`

This is **Partner Acceptance**. The Partner is reviewing Telectro's handling of a Partner-originated request.

### Telectro asks the Partner to perform work

\`\`\`text
Telectro assigns Partner fulfilment
→ Partner performs the work
→ Partner submits Work Done
→ Telectro reviews the submission
→ Partner corrects and resubmits when rework is required
→ Telectro performs the final review
\`\`\`

This is **Partner Work Completion**. Submitting Work Done does not itself mean Telectro has accepted the work.

# 1. Partner-originated requests and Partner Acceptance

## 1.1 Log a Partner service request

Partner-originated requests are created from the Partner-safe Partner Request page under the Partner organisation the logged-in user is authorised to represent.

${partnerRequestImage}

*The Partner Request page carries Partner organisation, Account, location, request type, subject, summary, and optional evidence context.*

## 1.2 Confirm the request was created

After submission, the request appears in the Partner's submitted-ticket list.

${partnerRequestCreatedImage}

*The new Partner-originated request is visible with its Open status and Telectro fulfilment responsibility.*

## 1.3 Review a Partner Acceptance request

When Telectro asks the Partner to review the outcome, the Partner-safe ticket page shows the acceptance request and the available Partner response actions.

${acceptancePendingImage}

*The Partner can submit an acceptance note or request rework from the Partner-safe ticket.*

## 1.4 Request rework when the outcome still needs correction

Use Request Rework when Telectro must correct, clarify, or complete something before the Partner can accept the outcome.

${acceptanceReworkDialogImage}

*Give a specific reason describing what still needs to be corrected.*

After submission, the Partner-safe ticket preserves the rework reason together with the earlier acceptance-request context.

${acceptanceReworkResultImage}

*The visible history shows \`Rework Required\` and explains why the request returned to Telectro.*

## 1.5 Review the corrected outcome when Telectro requests acceptance again

After Telectro addresses the rework request, the Partner may receive a renewed Partner Acceptance request.

${acceptanceAgainImage}

*The Partner-safe history shows the earlier rework request followed by Telectro's renewed request for acceptance.*

# 2. Partner Work Completion and rework

Partner Work Completion is the opposite workflow: Telectro has assigned fulfilment work to the Partner.

The Partner performs the work and submits Work Done. Telectro still reviews that submission before the work is accepted.

## 2.1 Respond when Telectro requests rework

If Telectro finds that the Work Done submission is incomplete or needs additional verification, the Partner-safe ticket changes to \`Rework Required\` and shows the reason.

${partnerWorkReworkImage}

*The Partner can see the previous Work Done note together with Telectro's rework requirement.*

## 2.2 Correct the work and submit Work Done again

After completing the requested correction or verification, submit Work Done again with a clear updated note.

${partnerWorkResubmittedImage}

*The corrected submission returns the Partner Work State to \`Work Completed by Partner\` and records the completion date.*

At that point the Partner submission is complete, but the Telectro review step is still outstanding. The Partner does not perform Telectro's internal review or closure actions.
`;

const generatedLines =
  generatedDocument.replace(/\r\n/g, "\n").split("\n");

const expectedPublicationHeadings = [
  "# 1. Partner-originated requests and Partner Acceptance",
  "# 2. Partner Work Completion and rework",
];

for (const heading of expectedPublicationHeadings) {
  if (countExactLine(generatedLines, heading) !== 1) {
    fail(
      `Generated Partner Visual Supplement heading is missing or duplicated: "${heading}".`,
    );
  }
}

const generatedNumberedHeadings =
  generatedLines.filter(
    (line) => /^# [1-2]\. /.test(line),
  );

if (generatedNumberedHeadings.length !== 2) {
  fail(
    `Expected 2 generated Partner visual chapters, found ${generatedNumberedHeadings.length}.`,
  );
}

for (const image of publicationImages) {
  if (!generatedDocument.includes(image)) {
    fail(
      `Generated Partner Visual Supplement is missing publication image "${image}".`,
    );
  }
}

const forbiddenImages = [
  "visual-15-request-partner-acceptance-dialog.png",
  "visual-19-telectro-partner-rework-received.png",
  "visual-20-request-partner-acceptance-again-dialog.png",
  "visual-22-partner-work-request-rework-dialog.png",
  "visual-23-telectro-partner-work-rework-required.png",
  "visual-26-partner-work-reviewed-by-telectro.png",
];

for (const forbiddenImage of forbiddenImages) {
  if (generatedDocument.includes(forbiddenImage)) {
    fail(
      `Generated Partner Visual Supplement contains Telectro-only visual "${forbiddenImage}".`,
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
  "=== Partner Visual Supplement extraction ===",
);

console.log(`SOURCE=${sourcePath}`);
console.log(`OUTPUT=${outputPath}`);
console.log("MASTER_PARTNER_CHAPTER_BOUNDARIES=PASS");
console.log("PARTNER_ACCEPTANCE_VISUAL_COUNT=6");
console.log("PARTNER_WORK_VISUAL_COUNT=2");
console.log("SELECTED_PARTNER_VISUAL_COUNT=8");
console.log("PARTNER_ACCEPTANCE_SOURCE_SCOPE=PASS");
console.log("PARTNER_WORK_SOURCE_SCOPE=PASS");
console.log("TELECTRO_ONLY_VISUAL_RESIDUE=0");
console.log("PARTNER_VISUAL_CHAPTER_COUNT=2");
console.log("PARTNER_VISUAL_SUPPLEMENT_EXTRACTION=PASS");
