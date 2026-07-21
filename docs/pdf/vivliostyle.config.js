// @ts-check

import { defineConfig } from "@vivliostyle/cli";

const publicationTitle =
  "ERPNext / Helpdesk Pilot Activity Process Guides";

export default defineConfig({
  title: publicationTitle,
  language: "en-ZA",
  size: "A4",

  theme: "./activity-process-guides.css",

  entryContext: "../user-guides",

  entry: [
    {
      path: "activity-process-guides.md",
      title: "Activity Process Guides",
    },
  ],

  toc: {
    title: "Contents",
    sectionDepth: 1,

    /*
     * There is only one source document. Remove the otherwise redundant
     * document-level wrapper and expose its H1 section list directly.
     */
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

    /*
     * Exclude the source document's introductory H1. Keep only the numbered
     * Activity Process Guide headings in the printed TOC and publication
     * navigation structure.
     */
    transformSectionList: (nodeList) => (propsList) => ({
      type: "element",
      tagName: "ol",
      properties: {},
      children: nodeList.flatMap((node, index) => {
        if (
          node.level === 1 &&
          node.headingText === publicationTitle
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

  workspaceDir: "dist/.vivliostyle",
  output: "dist/activity-process-guides.pdf",
});