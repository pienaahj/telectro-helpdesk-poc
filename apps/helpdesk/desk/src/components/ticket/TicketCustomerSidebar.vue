<template>
  <div class="flex w-[382px] flex-col border-l gap-4">
    <!-- Ticket ID -->
    <div class="flex items-center justify-between border-b px-5 py-3">
      <span class="cursor-copy text-lg font-semibold">Ticket details</span>
    </div>

    <!-- user info and sla info -->
    <div class="flex flex-col gap-4 pt-0 px-5 py-3 border-b">
      <!-- user info -->
      <div class="flex gap-2">
        <Avatar
          size="2xl"
          :image="ticket.data.contact.image"
          :label="ticket.data.contact.name"
        />
        <div class="flex items-center justify-between">
          <Tooltip :text="ticket.data.contact.name">
            <div class="w-[242px] truncate text-2xl font-medium">
              {{ ticket.data.contact.name }}
            </div>
          </Tooltip>
          <div class="flex gap-1.5" v-if="!ticket.data.feedback_rating">
            <Tooltip :text="ticket.data.contact.email_id">
              <Button class="h-7 w-7" @click="emit('open')">
                <template #icon>
                  <EmailIcon class="h-4 w-4" />
                </template>
              </Button>
            </Tooltip>
          </div>
        </div>
      </div>

      <!-- Ticket Info -->
      <div
        class="flex items-center text-base leading-5"
        v-for="field in ticketBasicInfo"
        :key="field.label"
      >
        <span class="w-[126px] text-sm text-gray-600">{{ field.label }}</span>
        <span
          class="text-base text-gray-800 flex-1"
          :class="!field.value && 'text-ink-gray-4'"
        >
          {{ field.value || "—" }}
        </span>
      </div>

      <!-- sla info -->
      <div
        v-for="data in slaData"
        :key="data.label"
        class="flex items-center text-base"
      >
        <div class="w-[126px] text-gray-600 text-sm">{{ data.title }}</div>

        <div class="break-words text-base text-gray-800">
          <Tooltip :text="dayjs(data.value).long()">
            <Badge :label="data.label" :theme="data.theme" variant="subtle" />
          </Tooltip>
        </div>
      </div>
    </div>

    <!-- feedback component -->
    <TicketFeedback
      v-if="ticket.data.feedback_rating"
      class="border-b text-base text-gray-600"
      :ticket="ticket.data"
    />

    <!-- Telectro Customer Location Context -->
    <div
      v-if="
        customerLocationContext &&
        (customerLocationContext.fault_point ||
          customerLocationContext.equipment_ref)
      "
      class="flex flex-col gap-3 border-b px-5 py-3 text-base"
    >
      <div class="text-sm font-medium text-gray-900">
        {{ __("Location details") }}
      </div>

      <div class="flex items-center text-base leading-5">
        <span class="w-[126px] text-sm text-gray-600">
          {{ __("Fault Point") }}
        </span>
        <span class="text-base text-gray-800 flex-1">
          {{ customerLocationContext.fault_point || "—" }}
        </span>
      </div>

      <div class="flex items-center text-base leading-5">
        <span class="w-[126px] text-sm text-gray-600">
          {{ __("Category") }}
        </span>
        <span class="text-base text-gray-800 flex-1">
          {{ customerLocationContext.category || "—" }}
        </span>
      </div>

      <div class="flex items-center text-base leading-5">
        <span class="w-[126px] text-sm text-gray-600">
          {{ __("Equipment Ref") }}
        </span>
        <span
          class="text-base text-gray-800 flex-1"
          :class="!customerLocationContext.equipment_ref && 'text-ink-gray-4'"
        >
          {{ customerLocationContext.equipment_ref || "—" }}
        </span>
      </div>

      <div
        v-if="customerLocationMapUrl"
        class="flex items-center text-base leading-5"
      >
        <span class="w-[126px] text-sm text-gray-600">
          {{ __("Map") }}
        </span>
        <a
          :href="customerLocationMapUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="font-semibold text-[#0f3d2e] underline underline-offset-4 hover:text-[#0a2b20]"
        >
          {{ __("View on map") }}
        </a>
      </div>
    </div>

    <!-- Additional ticket fields -->
    <div class="flex flex-col gap-4 pt-0 px-5 py-3 overflow-y-scroll">
      <div
        class="flex items-center text-base leading-5"
        v-for="field in ticketAdditionalInfo"
        :key="field.label"
      >
        <span class="w-[126px] text-sm text-gray-600">{{ field.label }}</span>
        <span
          class="text-base text-gray-800 flex-1"
          :class="!field.value && 'text-ink-gray-4'"
        >
          {{ field.value || "—" }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { dayjs } from "@/dayjs";
import { ITicket } from "@/pages/ticket/symbols";
import { Field } from "@/types";
import { formatTime } from "@/utils";
import { Avatar, Tooltip, call } from "frappe-ui";
import { computed, inject, ref, watch } from "vue";

const emit = defineEmits(["open"]);

const ticket = inject(ITicket);

const locationContextFieldnames = [
  "custom_site_group",
  "custom_fault_category",
  "custom_site",
  "custom_fault_asset",
  "custom_equipment_ref",
];

const customerLocationContext = ref({});

const customerLocationMapUrl = computed(() => {
  const lat = Number(customerLocationContext.value?.latitude || 0);
  const lon = Number(customerLocationContext.value?.longitude || 0);

  if (!lat || !lon) {
    return "";
  }

  const zoom = 19;

  return `https://www.openstreetmap.org/?mlat=${encodeURIComponent(
    lat,
  )}&mlon=${encodeURIComponent(lon)}#map=${zoom}/${encodeURIComponent(
    lat,
  )}/${encodeURIComponent(lon)}`;
});

async function loadCustomerLocationContext(ticketName: string) {
  if (!ticketName) {
    return;
  }

  customerLocationContext.value =
    (await call(
      "telephony.customer_location_lookup.get_customer_ticket_location_context",
      {
        ticket_name: ticketName,
      },
    )) || {};
}

watch(
  () => ticket.data?.name,
  (ticketName) => {
    if (ticketName) {
      loadCustomerLocationContext(ticketName);
    }
  },
  { immediate: true },
);

const slaData = computed(() => {
  const firstResponse = firstResponseData();
  const resolution = resolutionData();
  return [
    {
      title: "First Response",
      value: ticket.data.first_responded_on || ticket.data.response_by,
      label: firstResponse.label,
      theme: firstResponse.color,
    },
    {
      title: "Resolution",
      value: ticket.data.resolution_date || ticket.data.resolution_by,
      label: resolution.label,
      theme: resolution.color,
    },
  ];
});

function firstResponseData() {
  let firstResponse = null;
  if (
    !ticket.data.first_responded_on &&
    dayjs().isBefore(dayjs(ticket.data.response_by))
  ) {
    firstResponse = {
      label: `Due in ${formatTime(
        dayjs(ticket.data.response_by).diff(dayjs(), "s"),
      )}`,
      color: "orange",
    };
  } else if (
    dayjs(ticket.data.first_responded_on).isBefore(
      dayjs(ticket.data.response_by),
    )
  ) {
    firstResponse = {
      label: `Fulfilled in ${formatTime(
        dayjs(ticket.data.first_responded_on).diff(
          dayjs(ticket.data.creation),
          "s",
        ),
      )}`,
      color: "green",
    };
  } else {
    firstResponse = {
      label: "Failed",
      color: "red",
    };
  }
  return firstResponse;
}

function resolutionData() {
  let resolution = null;
  if (
    !ticket.data.resolution_date &&
    dayjs().isBefore(ticket.data.resolution_by)
  ) {
    resolution = {
      label: `Due in ${formatTime(
        dayjs(ticket.data.resolution_by).diff(dayjs(), "s"),
      )}`,
      color: "orange",
    };
  } else if (ticket.data.agreement_status === "Fulfilled") {
    resolution = {
      label: `Fulfilled in ${formatTime(
        dayjs(ticket.data.resolution_time, "s"),
      )}`,
      color: "green",
    };
  } else {
    resolution = {
      label: "Failed",
      color: "red",
    };
  }
  return resolution;
}

const ticketBasicInfo = computed(() => [
  {
    label: "Ticket ID",
    value: ticket.data.name,
  },
  {
    label: "Status",
    value: ticket.data.status,
    bold: true,
  },
]);

const ticketAdditionalInfo = computed(() => {
  const fields = [
    {
      label: "Subject",
      value: ticket.data.subject,
    },
    {
      label: "Team",
      value: ticket.data.agent_group || "-",
    },
    {
      label: "Priority",
      value: ticket.data.priority,
    },
  ];
  const custom_fields = ticket.data.template.fields
    .filter(
      (field: Field) =>
        !field.hide_from_customer &&
        ["subject", "team", "priority"].indexOf(field.fieldname) === -1 &&
        locationContextFieldnames.indexOf(field.fieldname) === -1,
    )
    .map((field: Field) => ({
      label: field.label,
      value: ticket.data[field.fieldname],
    }));

  return [...fields, ...custom_fields];
});
</script>
