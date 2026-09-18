<template>
  <div class="border-b border-[#e5ded2] bg-[#fbf8f2] px-5 py-4 md:bg-white">
    <!-- Telectro Customer Location Context -->
    <div
      v-if="
        customerLocationContext &&
        (customerLocationContext.fault_point ||
          customerLocationContext.affected_equipment ||
          customerLocationContext.equipment_ref)
      "
      class="mb-4 rounded-2xl border border-[#e5ded2] bg-[#fffdf8] p-4 text-sm shadow-sm"
    >
      <div class="mb-3 text-base font-semibold text-stone-950">
        {{ __("Location details") }}
      </div>

      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <span class="block text-xs font-medium uppercase text-stone-500">
            {{ __("Fault Point") }}
          </span>
          <span class="block break-words text-base font-medium text-gray-900">
            {{ customerLocationContext.fault_point || "—" }}
          </span>
        </div>

        <div>
          <span class="block text-xs font-medium uppercase text-stone-500">
            {{ __("Category") }}
          </span>
          <span class="block break-words text-base font-medium text-gray-900">
            {{ customerLocationContext.category || "—" }}
          </span>
        </div>

        <div>
          <span class="block text-xs font-medium uppercase text-stone-500">
            {{ __("Affected Equipment") }}
          </span>
          <span
            class="block break-words text-base font-medium text-gray-900"
            :class="
              !customerLocationContext.affected_equipment &&
              'text-ink-gray-4'
            "
          >
            {{ customerLocationContext.affected_equipment || "—" }}
          </span>
        </div>

        <div>
          <span class="block text-xs font-medium uppercase text-stone-500">
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
          <span class="block text-xs font-medium uppercase text-stone-500">
            {{ __("Map") }}
          </span>

          <div class="mt-1 flex flex-wrap gap-2">
            <a
              :href="customerLocationMapUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="rounded border border-[#7b836b] bg-[#7b836b] px-3 py-1.5 text-sm font-medium text-white hover:opacity-90"
            >
              {{ __("Aerial view") }}
            </a>

            <a
              v-if="customerOpenStreetMapUrl"
              :href="customerOpenStreetMapUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {{ __("Map view") }}
            </a>
          </div>
        </div>
      </div>
    </div>

    <div
      class="grid grid-cols-3 gap-4 rounded-2xl border border-[#e5ded2] bg-[#fffdf8] p-4 shadow-sm md:grid-cols-1"
    >
      <div class="space-y-1.5">
        <span class="block text-sm text-stone-950"> Status </span>
        <span class="block break-words text-base font-medium text-gray-900">
          {{ ticket.data.status }}
        </span>
      </div>

      <div class="space-y-1.5">
        <span class="block text-sm text-stone-950"> Priority </span>
        <span class="block break-words text-base font-medium text-gray-900">
          {{ ticket.data.priority }}
        </span>
      </div>

      <div v-for="data in slaData" :key="data.label" class="space-y-1.5">
        <Tooltip :text="dayjs(data.value).long()">
          <span class="block text-sm text-stone-950">{{ data.title }}</span>
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
        <span class="block text-sm text-stone-950">
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
  "custom_affected_equipment",
  "custom_equipment_ref",
];

const customerLocationContext = ref({});

const customerLocationMapUrl = computed(() => {
  const ticketName = String(ticket.data?.name || "").trim();
  const lat = Number(customerLocationContext.value?.latitude || 0);
  const lon = Number(customerLocationContext.value?.longitude || 0);

  if (!ticketName || !lat || !lon) {
    return "";
  }

  return `/helpdesk/my-tickets/${encodeURIComponent(ticketName)}/map`;
});

const customerOpenStreetMapUrl = computed(() => {
  const lat = Number(
    customerLocationContext.value?.latitude || 0,
  );

  const lon = Number(
    customerLocationContext.value?.longitude || 0,
  );

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
