<template>
  <div class="border-b px-5 py-3">
    <!-- Telectro Customer Location Context -->
    <div
      v-if="
        customerLocationContext &&
        (customerLocationContext.fault_point ||
          customerLocationContext.equipment_ref)
      "
      class="mb-4 rounded border border-gray-200 bg-gray-50 p-3 text-sm"
    >
      <div class="mb-3 font-medium text-gray-900">
        {{ __("Location details") }}
      </div>

      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <span class="block text-xs font-medium uppercase text-gray-500">
            {{ __("Fault Point") }}
          </span>
          <span class="block break-words text-base font-medium text-gray-900">
            {{ customerLocationContext.fault_point || "—" }}
          </span>
        </div>

        <div>
          <span class="block text-xs font-medium uppercase text-gray-500">
            {{ __("Category") }}
          </span>
          <span class="block break-words text-base font-medium text-gray-900">
            {{ customerLocationContext.category || "—" }}
          </span>
        </div>

        <div>
          <span class="block text-xs font-medium uppercase text-gray-500">
            {{ __("Equipment Ref") }}
          </span>
          <span
            class="block break-words text-base font-medium text-gray-900"
            :class="!customerLocationContext.equipment_ref && 'text-ink-gray-4'"
          >
            {{ customerLocationContext.equipment_ref || "—" }}
          </span>
        </div>

        <div v-if="customerLocationMapUrl">
          <span class="block text-xs font-medium uppercase text-gray-500">
            {{ __("Map") }}
          </span>
          <a
            :href="customerLocationMapUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="text-base font-medium text-blue-600 hover:underline"
          >
            {{ __("View on map") }}
          </a>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-4 md:grid-cols-1">
      <div class="space-y-1.5">
        <span class="block text-sm text-gray-700"> Status </span>
        <span class="block break-words text-base font-medium text-gray-900">
          {{ ticket.data.status }}
        </span>
      </div>

      <div class="space-y-1.5">
        <span class="block text-sm text-gray-700"> Priority </span>
        <span class="block break-words text-base font-medium text-gray-900">
          {{ ticket.data.priority }}
        </span>
      </div>

      <div v-for="data in slaData" :key="data.label" class="space-y-1.5">
        <Tooltip :text="dayjs(data.value).long()">
          <span class="block text-sm text-gray-700">{{ data.title }}</span>
        </Tooltip>
        <span class="block break-words text-base font-medium text-gray-900">
          <Badge
            v-if="data.showSla"
            :label="data.label"
            :theme="data.theme"
            variant="outline"
          />
          <span v-else>
            {{ dayjs.tz(data.value).fromNow() }}
          </span>
        </span>
      </div>

      <div
        v-for="field in customFields"
        :key="field.fieldname"
        class="space-y-1.5"
      >
        <span class="block text-sm text-gray-700">
          {{ field.label }}
        </span>
        <span
          class="block break-words text-base font-medium text-gray-900"
          :class="!ticket.data[field.fieldname] && 'text-ink-gray-4'"
        >
          {{ ticket.data[field.fieldname] || "—" }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { dayjs } from "@/dayjs";
import { Field } from "@/types";
import { call } from "frappe-ui";
import { computed, inject, ref, watch } from "vue";
import { ITicket } from "./symbols";

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
        ticket_name: String(ticketName),
      },
    )) || {};
}

watch(
  () => ticket.data?.name,
  (ticketName) => {
    if (ticketName) {
      loadCustomerLocationContext(String(ticketName));
    }
  },
  { immediate: true },
);

const slaData = computed(() => {
  const responseSla =
    ticket.data.first_responded_on &&
    dayjs(ticket.data.first_responded_on).isBefore(ticket.data.response_by)
      ? "Fulfilled"
      : "Failed";

  if (ticket.data.priority === "Unclassified") {
    return [
      {
        title: "Expected First Response",
        showSla: ticket.data.first_responded_on,
        label: responseSla,
        theme: responseSla === "Fulfilled" ? "green" : "red",
        value: ticket.data.response_by,
      },
    ];
  }

  const resolutionSla =
    ticket.data.resolution_date &&
    dayjs(ticket.data.resolution_date).isBefore(ticket.data.resolution_by)
      ? "Fulfilled"
      : "Failed";

  return [
    {
      title: "Expected First Response",
      showSla: ticket.data.first_responded_on,
      label: responseSla,
      theme: responseSla === "Fulfilled" ? "green" : "red",
      value: ticket.data.response_by,
    },
    {
      title: "Expected Resolution",
      showSla: ticket.data.resolution_date,
      label: resolutionSla,
      theme: resolutionSla === "Fulfilled" ? "green" : "red",
      value: ticket.data.resolution_by,
    },
  ];
});

const customFields = computed(() => {
  const _custom_fields = ticket.data.template.fields
    .filter((field: Field) => !field.hide_from_customer)
    .filter(
      (f: Field) =>
        ["subject", "team", "priority"].indexOf(f.fieldname) === -1 &&
        locationContextFieldnames.indexOf(f.fieldname) === -1,
    );
  return _custom_fields;
});
</script>
