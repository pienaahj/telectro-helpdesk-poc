<template>
  <div v-if="ticket.data" class="flex flex-col">
    <LayoutHeader>
      <template #left-header>
        <div
          v-if="isMobileView"
          class="flex w-full min-w-0 items-center gap-1 text-lg font-medium"
        >
          <RouterLink
            :to="{ name: 'TicketsCustomer' }"
            class="min-w-0 truncate text-ink-gray-6"
          >
            {{ __("Support Requests") }}
          </RouterLink>

          <span class="shrink-0 text-ink-gray-5">/</span>

          <RouterLink
            :to="{ name: 'TicketCustomer' }"
            class="shrink-0 text-ink-gray-9"
            aria-current="page"
          >
            #{{ ticket.data.name }}
          </RouterLink>
        </div>

        <div v-else class="min-w-0 max-w-full overflow-hidden">
          <Breadcrumbs :items="breadcrumbs" />
        </div>
      </template>
      <template #right-header>
        <CustomActions
          v-if="ticket.data._customActions"
          :actions="ticket.data._customActions"
        />
        <Button
          v-if="allowCustomerTicketClose && ticket.data.status !== 'Closed'"
          :label="__('Close')"
          theme="gray"
          variant="solid"
          @click="handleClose()"
        >
          <template #prefix>
            <LucideCheck class="size-4" />
          </template>
        </Button>
      </template>
    </LayoutHeader>
    <div
      class="mx-6 mt-4 rounded-xl border border-stone-200 bg-[#f8f5ef] px-5 py-4 shadow-sm md:mx-10"
    >
      <div
        class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between"
      >
        <div class="flex items-center gap-4">
          <img
            :src="boschendalLogoUrl"
            alt="Boschendal"
            class="h-10 w-auto shrink-0"
          />
          <div>
            <div class="text-sm uppercase tracking-[0.18em] text-stone-500">
              {{ __("Boschendal Service Desk") }}
            </div>
            <div class="text-lg font-semibold text-stone-950">
              {{ __("Support request") }} #{{ ticket.data.name }}
            </div>
          </div>
        </div>

        <div class="text-sm text-stone-600">
          {{ __("Managed by Telectro") }}
        </div>
      </div>
    </div>
    <div class="flex min-h-0 w-full flex-1 overflow-visible md:overflow-hidden">
      <!-- Main Ticket Comm -->
      <section
        class="flex min-h-0 w-full flex-1 flex-col pb-8 md:max-w-[calc(100%-382px)]"
      >
        <!-- show for only mobile -->
        <TicketCustomerTemplateFields v-if="isMobileView" />

        <div
          v-if="isMobileView && originalCustomerRequest"
          class="mx-6 mt-4 rounded-xl border border-stone-200 bg-white p-4 shadow-sm md:mx-10"
        >
          <div class="mb-1 text-sm font-medium text-gray-900">
            {{ __("Request details") }}
          </div>

          <div class="mb-2 text-sm text-gray-600">
            {{
              originalCustomerRequest.user?.name ||
              originalCustomerRequest.sender ||
              __("Customer request")
            }}
            ·
            {{ dayjs(originalCustomerRequest.creation).fromNow() }}
          </div>

          <div
            class="text-base text-gray-800"
            v-html="originalCustomerRequest.content"
          />
        </div>

        <div
          v-if="
            latestCustomerVisibleUpdate &&
            latestCustomerVisibleUpdate.name !== originalCustomerRequest?.name
          "
          class="mx-6 mt-4 rounded-xl border border-stone-200 bg-white p-4 shadow-sm md:mx-10"
        >
          <div class="mb-1 text-sm font-medium text-gray-900">
            {{ __("Latest update") }}
          </div>

          <div class="mb-2 text-sm text-gray-600">
            {{
              latestCustomerVisibleUpdate.user?.name ||
              latestCustomerVisibleUpdate.sender ||
              __("Update")
            }}
            ·
            {{ dayjs(latestCustomerVisibleUpdate.creation).fromNow() }}
          </div>

          <div
            class="max-h-24 overflow-hidden text-base text-gray-800"
            v-html="latestCustomerVisibleUpdate.content"
          />
        </div>

        <TicketConversation class="grow" />

        <div v-if="showEditor" class="border-t bg-surface-white px-5 pt-4">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div>
              <div class="text-base font-medium text-ink-gray-8">
                {{ __("Add more information") }}
              </div>
              <div class="text-sm text-ink-gray-6">
                {{
                  __(
                    "Send photos, equipment labels, access notes, or extra location details to the Telectro team.",
                  )
                }}
              </div>
            </div>
            <Button
              :label="__('Add information')"
              theme="gray"
              variant="solid"
              @click="openCustomerUpdateEditor"
            />
          </div>
        </div>
        <div
          class="w-full px-5 pb-8 pt-5 md:pb-5"
          @keydown.ctrl.enter.capture.stop="sendEmail"
          @keydown.meta.enter.capture.stop="sendEmail"
        >
          <TicketTextEditor
            v-if="showEditor"
            ref="editor"
            v-model:attachments="attachments"
            v-model:content="editorContent"
            v-model:expand="isExpanded"
            :placeholder="
              __('Add photos, labels, access notes, or extra location details')
            "
            autofocus
            @clear="() => (isExpanded = false)"
            :uploadFunction="
              (file: any) => uploadFunction(file, 'HD Ticket', props.ticketId)
            "
          >
            <template #bottom-right>
              <Button
                :label="__('Send')"
                theme="gray"
                variant="solid"
                :disabled="$refs.editor?.editor.isEmpty || send.loading"
                :loading="send.loading"
                @click="sendEmail"
              />
            </template>
          </TicketTextEditor>
        </div>
      </section>
      <!-- Ticket Sidebar only for desktop view-->
      <TicketCustomerSidebar v-if="!isMobileView" @open="isExpanded = true" />
    </div>
    <TicketFeedback v-model:open="showFeedbackDialog" />
  </div>
</template>

<script setup lang="ts">
import { dayjs } from "@/dayjs";
import { LayoutHeader } from "@/components";
import TicketCustomerSidebar from "@/components/ticket/TicketCustomerSidebar.vue";
import { setupCustomizations } from "@/composables/formCustomisation";
import { useActiveViewers } from "@/composables/realtime";
import { useScreenSize } from "@/composables/screen";
import { socket } from "@/socket";
import { useConfigStore } from "@/stores/config";
import { globalStore } from "@/stores/globalStore";
import { useTicketStatusStore } from "@/stores/ticketStatus";
import { isContentEmpty, isCustomerPortal, uploadFunction } from "@/utils";
import { Breadcrumbs, Button, call, createResource, toast } from "frappe-ui";
import { __ } from "@/translation";
import {
  computed,
  defineAsyncComponent,
  onMounted,
  onUnmounted,
  provide,
  ref,
} from "vue";
import { useRouter } from "vue-router";
import { ITicket } from "./symbols";
import TicketConversation from "./TicketConversation.vue";
import TicketCustomerTemplateFields from "./TicketCustomerTemplateFields.vue";
import TicketFeedback from "./TicketFeedback.vue";
const TicketTextEditor = defineAsyncComponent(
  () => import("./TicketTextEditor.vue"),
);

interface P {
  ticketId: string;
}
const router = useRouter();

const props = defineProps<P>();

const { getStatus } = useTicketStatusStore();

const ticket = createResource({
  url: "helpdesk.helpdesk.doctype.hd_ticket.api.get_one",
  cache: ["Ticket", props.ticketId],
  params: {
    name: props.ticketId,
    is_customer_portal: isCustomerPortal.value,
  },
  auto: true,
  onSuccess: (data) => {
    data.status = getStatus(data.status)?.label_customer;
    setupCustomizations(ticket, {
      doc: data,
      call,
      router,
      toast,
      $dialog,
      updateField,
      createToast: toast.create,
    });
  },
  onError: () => {
    toast.error(__("Ticket not found"));
    router.replace("/my-tickets");
  },
});

provide(ITicket, ticket);
const editor = ref(null);
const editorContent = ref("");
const attachments = ref([]);
const showFeedbackDialog = ref(false);
const isExpanded = ref(false);

const { isMobileView } = useScreenSize();
const { $dialog } = globalStore();

const boschendalLogoUrl = "/assets/telephony/images/boschendal-logo.svg";

const send = createResource({
  url: "run_doc_method",
  debounce: 300,
  makeParams: () => ({
    dt: "HD Ticket",
    dn: props.ticketId,
    method: "create_communication_via_contact",
    args: {
      message: editorContent.value,
      attachments: attachments.value,
    },
  }),
  onSuccess: () => {
    editor.value.editor.commands.clearContent(true);
    attachments.value = [];
    isExpanded.value = false;
    ticket.reload();
  },
});

function updateField(name, value, callback = () => {}) {
  updateTicket(name, value);
  callback();
}

function sendEmail() {
  if (isContentEmpty(editorContent.value) || send.loading) {
    return;
  }
  send.submit();
}

function openCustomerUpdateEditor() {
  isExpanded.value = true;
  setTimeout(() => {
    editor.value?.editor?.commands?.focus?.();
  }, 0);
}

function updateTicket(fieldname: string, value: string) {
  createResource({
    url: "frappe.client.set_value",
    params: {
      doctype: "HD Ticket",
      name: props.ticketId,
      fieldname,
      value,
    },
    auto: true,
    onSuccess: () => {
      ticket.reload();
      toast.success(__("Ticket updated"));
    },
  });
}

function handleClose() {
  if (showFeedback.value) {
    showFeedbackDialog.value = true;
  } else {
    showConfirmationDialog();
  }
}

function showConfirmationDialog() {
  $dialog({
    title: __("Close Ticket"),
    message: __("Are you sure you want to close this ticket?"),
    actions: [
      {
        label: __("Confirm"),
        variant: "solid",
        onClick(close: Function) {
          ticket.data.status = "Closed";
          setValue.submit(
            { fieldname: "status", value: "Closed" },
            {
              onSuccess: () => {
                toast.success(__("Ticket closed"));
              },
            },
          );
          close();
        },
      },
    ],
  });
}

const setValue = createResource({
  url: "frappe.client.set_value",
  debounce: 300,
  makeParams: (params) => {
    return {
      doctype: "HD Ticket",
      name: props.ticketId,
      fieldname: params.fieldname,
      value: params.value,
    };
  },
  onSuccess: () => {
    showFeedbackDialog.value = false;
    ticket.reload();
  },
});

const breadcrumbs = computed(() => {
  const items = [
    { label: __("Support Requests"), route: { name: "TicketsCustomer" } },
  ];

  items.push({
    label: ticket.data?.subject,
    route: { name: "TicketCustomer" },
  });

  return items;
});

const allowCustomerTicketClose = computed(() => false);

const showEditor = computed(() => ticket.data.status !== "Closed");

const customerVisibleCommunications = computed(() => {
  return [...(ticket.data?.communications || [])].sort(
    (a, b) => new Date(a.creation).getTime() - new Date(b.creation).getTime(),
  );
});

const originalCustomerRequest = computed(() => {
  return customerVisibleCommunications.value[0] || null;
});

const latestCustomerVisibleUpdate = computed(() => {
  if (customerVisibleCommunications.value.length <= 1) {
    return null;
  }

  return customerVisibleCommunications.value[
    customerVisibleCommunications.value.length - 1
  ];
});

// this handles whether the ticket was raised and then was closed without any reply from the agent.
const { isFeedbackMandatory } = useConfigStore();
const showFeedback = computed(() => {
  const hasAgentCommunication = ticket.data?.communications?.some(
    (c) => c.sender !== ticket.data.raised_by,
  );
  return hasAgentCommunication && isFeedbackMandatory;
});
const { startViewing, stopViewing } = useActiveViewers(props.ticketId);
onMounted(() => {
  startViewing(props.ticketId);
  document.title = props.ticketId;

  socket.on("helpdesk:ticket-update", ({ ticket_id }) => {
    if (ticket_id === props.ticketId) {
      ticket.reload();
    }
  });
});

onUnmounted(() => {
  stopViewing(props.ticketId);
  document.title = "Helpdesk";
  socket.off("helpdesk:ticket-update");
});
</script>
