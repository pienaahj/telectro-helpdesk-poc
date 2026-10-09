
import customerVisualConfig from "./vivliostyle.customer-visual-supplement.config.js";

const documentTitle =
  "Emerald Life Customer Activity Process Guides Visual Supplement";

export default {
  ...customerVisualConfig,

  title: `ERPNext / Helpdesk Pilot ${documentTitle}`,

  entry: [
    {
      path: "pdf/dist/emerald-life-customer-activity-process-guides-visual-supplement.md",
      title: documentTitle,
    },
  ],

  toc: {
    ...customerVisualConfig.toc,

    transformSectionList: (nodeList) => (propsList) => ({
      type: "element",
      tagName: "ol",
      properties: {},
      children: nodeList.flatMap((node, index) => {
        if (
          node.level === 1 &&
          node.headingText === documentTitle
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

  workspaceDir:
    "dist/.vivliostyle-emerald-life-customer-visual-supplement",

  output:
    "dist/emerald-life-customer-activity-process-guides-visual-supplement.pdf",
};
