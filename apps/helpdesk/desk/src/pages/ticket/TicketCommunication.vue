<template>
  <div
    class="border flex-1 px-3 pt-2.5 mb-4 border-transparent bg-surface-white rounded-md shadow text-base leading-6 transition-all duration-300 ease-in-out"
  >
    <div class="mb-4 flex items-center justify-between text-base">
      <div class="flex items-center gap-0.5">
        <UserAvatar v-bind="user" size="lg" expand strong :hide-avatar="true" />
        <LucideDot class="text-gray-500 size-4" />
        <Tooltip :text="dayjs(date).long()">
          <span class="text-gray-600">
            {{ dayjs.tz(date).fromNow() }}
          </span>
        </Tooltip>
      </div>
    </div>

    <EmailContent :content="sanitize(content)" />
    <div class="flex flex-wrap gap-2 mb-2">
      <AttachmentItem
        v-for="a in attachments"
        :key="a.file_id"
        :label="a.file_name"
        :url="attachmentUrl(a)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { AttachmentItem, UserAvatar } from "@/components";
import { dayjs } from "@/dayjs";
import { UserInfo } from "@/types";
import { Tooltip } from "frappe-ui";
import sanitizeHtml from "sanitize-html";

interface Attachment {
  file_id: string;
  file_name: string;
}

interface P {
  content: string;
  date: string;
  user: UserInfo;
  cc?: string;
  bcc?: string;
  attachments?: Attachment[];
  ticketName?: string;
}

const props = withDefaults(defineProps<P>(), {
  cc: () => "",
  bcc: () => "",
  attachments: () => [],
  ticketName: "",
});

function sanitize(html: string) {
  return sanitizeHtml(html, {
    allowedTags: sanitizeHtml.defaults.allowedTags.concat(["img", "video"]),
    allowedAttributes: {
      a: ["href"],
      video: ["src", "controls"],
      img: ["src"],
    },
  });
}

function attachmentUrl(a: Attachment): string {
  return `/api/method/telephony.customer_ticket_resolution.download_customer_completion_evidence?ticket_name=${encodeURIComponent(
    props.ticketName,
  )}&file_id=${encodeURIComponent(a.file_id)}`;
}
</script>
