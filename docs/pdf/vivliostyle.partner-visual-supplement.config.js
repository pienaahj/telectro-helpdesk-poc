// @ts-check

import { defineConfig } from "@vivliostyle/cli";

const publicationTitle =
  "ERPNext / Helpdesk Pilot Partner Activity Process Guides Visual Supplement";

export default defineConfig({
  title: publicationTitle,
  language: "en-ZA",
  size: "A4",

  theme: "./activity-process-guides.css",

  entryContext: "..",

  entry: [
    {
      path: "pdf/dist/partner-activity-process-guides-visual-supplement.md",
      title: "Partner Activity Process Guides Visual Supplement",
    },
  ],

  toc: {
    title: "Contents",
    sectionDepth: 1,

    transformDocumentList: (_nodeList) => (propsList) => {
      const children = propsList[0].children;

      if (Array.isArray(children)) {
        return children.length === 1
          ? children[0]
          : {
              type: "root",
              children,
            };
      }

      return children;
    },

    transformSectionList: (nodeList) => (propsList) => ({
      type: "element",
      tagName: "ol",
      properties: {},
      children: nodeList.flatMap((node, index) => {
        if (
          node.level === 1 &&
          node.headingText ===
            "Partner Activity Process Guides Visual Supplement"
        ) {
          return [];
        }

        const nestedChildren = propsList[index].children;
        const label = {
          type: "text",
          value: node.headingText,
        };

        return [
          {
            type: "element",
            tagName: "li",
            properties: {
              dataSectionLevel: node.level,
            },
            children: [
              node.href
                ? {
                    type: "element",
                    tagName: "a",
                    properties: {
                      href: node.href,
                    },
                    children: [label],
                  }
                : {
                    type: "element",
                    tagName: "span",
                    properties: {},
                    children: [label],
                  },

              ...(Array.isArray(nestedChildren)
                ? nestedChildren
                : [nestedChildren]),
            ],
          },
        ];
      }),
    }),
  },

  workspaceDir: "dist/.vivliostyle-partner-visual-supplement",
  output: "dist/partner-activity-process-guides-visual-supplement.pdf",
});
