<template>
  <div class="flex flex-col overflow-y-auto">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <CustomActions
          v-if="template.data?._customActions"
          :actions="template.data?._customActions"
        />
      </template>
    </LayoutHeader>
    <!-- Container -->
    <div
      class="flex flex-col gap-5 py-6 h-full flex-1 self-center overflow-auto mx-auto w-full max-w-4xl px-5"
    >
      <!-- custom fields descriptions -->
      <div v-if="Boolean(template.data?.about)" class="">
        <div class="prose-f" v-html="sanitize(template.data.about)" />
      </div>
      <!-- custom fields -->
      <div
        class="grid grid-cols-1 gap-4 sm:grid-cols-3"
        v-if="Boolean(visibleFields)"
      >
        <UniInput
          v-for="field in visibleFields"
          :key="field.fieldname"
          :field="field"
          :value="templateFields[field.fieldname]"
          @change="
            (e) => handleOnFieldChange(e, field.fieldname, field.fieldtype)
          "
        />
      </div>
      <!-- Telectro Customer Fault Point prototype -->
      <div
        v-if="isCustomerPortal"
        class="rounded border border-gray-200 bg-white p-4 space-y-3"
      >
        <div>
          <span class="block text-sm font-medium text-gray-700">
            {{ __("Fault Point") }}
          </span>
          <span class="block text-sm text-gray-500">
            {{
              __(
                "Optional. Choose the affected Boschendal location. You can browse the available options or search if you know the name. Results are limited to your Customer organisation.",
              )
            }}
          </span>
        </div>

        <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div class="flex flex-col gap-1">
            <span class="text-sm text-gray-700">{{ __("Category") }}</span>
            <select
              v-model="faultPointCategory"
              class="form-control rounded border border-gray-300 px-3 py-2 text-sm"
              @change="handleFaultPointCategoryChange"
            >
              <option
                v-for="category in faultPointCategories"
                :key="category"
                :value="category"
              >
                {{ category }}
              </option>
            </select>
          </div>

          <div class="flex flex-col gap-1 sm:col-span-2">
            <span class="text-sm text-gray-700">{{ __("Search") }}</span>
            <div class="flex gap-2">
              <FormControl
                v-model="faultPointSearch"
                type="text"
                :placeholder="
                  __('Search within the selected category, e.g. Bakery')
                "
                @keyup.enter="searchFaultPoints"
              />
              <Button
                :label="__('Search')"
                theme="gray"
                variant="solid"
                :loading="faultPointLoading"
                @click="searchFaultPoints"
              />
            </div>
          </div>
        </div>

        <div
          v-if="selectedFaultPoint"
          class="rounded border border-gray-200 bg-gray-50 p-4 text-sm"
        >
          <div class="mb-3 flex items-start justify-between gap-3">
            <div>
              <div class="font-medium text-gray-900">
                {{ selectedFaultPointLabel }}
              </div>
              <div class="text-xs text-gray-500">
                {{
                  selectedFaultPointIsNonPoint
                    ? __(
                        "This link or area will be sent to Telectro with your ticket.",
                      )
                    : __(
                        "This location will be sent to Telectro with your ticket.",
                      )
                }}
              </div>
            </div>

            <Button
              :label="__('Clear')"
              theme="gray"
              variant="subtle"
              @click="clearFaultPointSelection"
            />
          </div>

          <div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <div>
              <div class="text-xs font-medium uppercase text-gray-500">
                {{
                  selectedFaultPointIsNonPoint
                    ? __("Fault Asset")
                    : __("Fault Point")
                }}
              </div>
              <div class="text-gray-900">
                {{ selectedFaultPoint.location_name }}
              </div>
            </div>

            <div>
              <div class="text-xs font-medium uppercase text-gray-500">
                {{ __("Category") }}
              </div>
              <div class="text-gray-900">
                {{ faultPointCategory }}
              </div>
            </div>

            <div>
              <div class="text-xs font-medium uppercase text-gray-500">
                {{ __("Campus") }}
              </div>
              <div class="text-gray-900">
                {{ selectedFaultPointCampus }}
              </div>
            </div>

            <div>
              <div class="text-xs font-medium uppercase text-gray-500">
                {{ __("Map") }}
              </div>
              <div class="text-gray-900">
                <a
                  v-if="selectedFaultPointHasCoordinates"
                  :href="selectedFaultPointMapUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-blue-600 hover:underline"
                >
                  {{ __("View on map") }}
                </a>
                <span v-else>
                  {{
                    selectedFaultPointIsNonPoint
                      ? __("Not available for this geometry")
                      : __("Not available")
                  }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="faultPointLoading && !selectedFaultPoint"
          class="rounded border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700"
        >
          {{ __("Loading available fault points...") }}
        </div>

        <div v-if="faultPointResults.length" class="space-y-2">
          <div class="text-xs text-gray-500">
            {{
              faultPointSearch
                ? __(
                    "Matching fault points. Select the closest affected location.",
                  )
                : __(
                    "Available fault points. Scroll or search to find the closest affected location.",
                  )
            }}
          </div>

          <div
            class="max-h-80 space-y-2 overflow-y-auto rounded border border-gray-200 p-2"
          >
            <button
              v-for="row in faultPointResults"
              :key="row.name"
              type="button"
              class="block w-full rounded border border-gray-200 px-3 py-2 text-left text-sm hover:bg-gray-50"
              @click="selectFaultPoint(row)"
            >
              <span class="block font-medium text-gray-900">
                {{ row.location_name }}
              </span>
              <span class="block text-xs text-gray-500">
                {{ row.parent_location }}
              </span>
            </button>
          </div>
        </div>
        <div
          v-else-if="
            faultPointSearched && !faultPointLoading && !selectedFaultPoint
          "
          class="rounded border border-orange-200 bg-orange-50 p-3 text-sm text-orange-800"
        >
          <div class="font-medium">
            {{ __("No matching fault points found.") }}
          </div>
          <div class="mt-1">
            {{
              __(
                "Try a shorter search term, choose the nearest known location, or select the closest point you recognise and describe the exact place in the details below.",
              )
            }}
          </div>
        </div>
      </div>
      <!-- existing fields -->
      <div
        class="flex flex-col"
        :class="(subject.length >= 2 || description.length) && 'gap-5'"
      >
        <div class="flex flex-col gap-2">
          <span class="block text-sm text-gray-700">
            {{ __("Subject") }}
            <span class="place-self-center text-red-500"> * </span>
          </span>
          <FormControl
            v-model="subject"
            type="text"
            :placeholder="__('A short description')"
          />
        </div>
        <SearchArticles
          v-if="isCustomerPortal"
          :query="subject"
          class="shadow"
        />
        <div v-if="isCustomerPortal">
          <h4
            v-show="subject.length <= 2 && description.length === 0"
            class="text-p-sm text-gray-500 ml-1"
          >
            {{ __("Please enter a subject to continue") }}
          </h4>
          <TicketTextEditor
            v-show="subject.length > 2 || description.length > 0"
            ref="editor"
            v-model:attachments="attachments"
            v-model:content="description"
            :placeholder="__('Detailed explanation')"
            expand
            :uploadFunction="(file: any) => uploadFunction(file)"
          >
            <template #bottom-right>
              <Button
                :label="__('Submit')"
                theme="gray"
                variant="solid"
                :disabled="
                  $refs.editor.editor.isEmpty || ticket.loading || !subject
                "
                @click="() => ticket.submit()"
              />
            </template>
          </TicketTextEditor>
        </div>
      </div>

      <!-- for agent portal -->
      <div v-if="!isCustomerPortal">
        <TicketTextEditor
          ref="editor"
          v-model:attachments="attachments"
          v-model:content="description"
          :placeholder="__('Detailed explanation')"
          expand
        >
          <template #bottom-right>
            <Button
              :label="__('Submit')"
              theme="gray"
              variant="solid"
              :disabled="
                $refs.editor.editor.isEmpty || ticket.loading || !subject
              "
              @click="() => ticket.submit()"
            />
          </template>
        </TicketTextEditor>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { LayoutHeader, UniInput } from "@/components";
import {
  handleLinkFieldUpdate,
  handleSelectFieldUpdate,
  parseField,
  setupCustomizations,
} from "@/composables/formCustomisation";
import { useAuthStore } from "@/stores/auth";
import { globalStore } from "@/stores/globalStore";
import { capture } from "@/telemetry";
import { Field } from "@/types";
import { isCustomerPortal, uploadFunction } from "@/utils";
import {
  Breadcrumbs,
  Button,
  call,
  createResource,
  FormControl,
  usePageMeta,
} from "frappe-ui";
import { __ } from "@/translation";
import { useOnboarding } from "frappe-ui/frappe";
import sanitizeHtml from "sanitize-html";
import {
  computed,
  defineAsyncComponent,
  onMounted,
  reactive,
  ref,
  watch,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import SearchArticles from "../../components/SearchArticles.vue";
const TicketTextEditor = defineAsyncComponent(
  () => import("./TicketTextEditor.vue"),
);

interface P {
  templateId?: string;
}

const props = withDefaults(defineProps<P>(), {
  templateId: "",
});

const route = useRoute();
const router = useRouter();
const { $dialog } = globalStore();
const { updateOnboardingStep } = useOnboarding("helpdesk");
const { isManager, userId: userID } = useAuthStore();

const subject = ref("");
const description = ref("");
const attachments = ref([]);
const templateFields = reactive({});

const faultPointCategories = [
  "Buildings",
  "Network Nodes",
  "Links",
  "Areas",
  "Other",
  "Residents",
];

const faultPointCategory = ref("Buildings");
const faultPointSearch = ref("");
const faultPointResults = ref([]);
const selectedFaultPoint = ref(null);
const faultPointLoading = ref(false);
const faultPointSearched = ref(false);

const template = createResource({
  url: "helpdesk.helpdesk.doctype.hd_ticket_template.api.get_one",
  makeParams: () => ({
    name: props.templateId || "Default",
  }),
  auto: true,
  onSuccess: (data) => {
    description.value = data.description_template || "";
    oldFields = window.structuredClone(data.fields || []);
    setupCustomizations(template, {
      doc: templateFields,
      call,
      router,
      $dialog,
      applyFilters,
    });
    setupTemplateFields(data.fields);
  },
});

function setupTemplateFields(fields) {
  fields.forEach((field: Field) => {
    templateFields[field.fieldname] = "";
  });
}

let oldFields = [];

function applyFilters(fieldname: string, filters: any = null) {
  const f: Field = template.data.fields.find((f) => f.fieldname === fieldname);
  if (!f) return;
  if (f.fieldtype === "Select") {
    handleSelectFieldUpdate(f, fieldname, filters, templateFields, oldFields);
  } else if (f.fieldtype === "Link") {
    handleLinkFieldUpdate(f, fieldname, filters, templateFields, oldFields);
  }
}

const customOnChange = computed(() => template.data?._customOnChange);

const visibleFields = computed(() => {
  let _fields = template.data?.fields?.filter(
    (f) => !isCustomerPortal.value || !f.hide_from_customer,
  );
  if (!_fields) return [];
  return _fields.map((field) => parseField(field, templateFields));
});

function handleOnFieldChange(e: any, fieldname: string, fieldtype: string) {
  templateFields[fieldname] = e.value;
  const fieldDependentFns = customOnChange.value?.[fieldname];
  if (fieldDependentFns) {
    fieldDependentFns.forEach((fn: Function) => {
      fn(e.value, fieldtype);
    });
  }
}

const selectedFaultPointGeometryType = computed(() => {
  return selectedFaultPoint.value?.custom_kmz_geometry_type || "";
});

const selectedFaultPointIsNonPoint = computed(() => {
  return ["LineString", "Polygon"].includes(
    selectedFaultPointGeometryType.value,
  );
});

const selectedFaultPointLabel = computed(() => {
  if (selectedFaultPointIsNonPoint.value) {
    return __("Selected Fault Asset");
  }

  return __("Selected Fault Point");
});

const selectedFaultPointCampus = computed(() => {
  const parent = selectedFaultPoint.value?.parent_location || "";
  const category = faultPointCategory.value || "";

  if (parent && category && parent.endsWith(` - ${category}`)) {
    return parent.slice(0, -` - ${category}`.length);
  }

  return parent || "";
});

const selectedFaultPointHasCoordinates = computed(() => {
  const lat = Number(selectedFaultPoint.value?.latitude || 0);
  const lon = Number(selectedFaultPoint.value?.longitude || 0);

  return lat !== 0 && lon !== 0;
});

const selectedFaultPointMapUrl = computed(() => {
  if (!selectedFaultPointHasCoordinates.value) {
    return "";
  }

  const lat = Number(selectedFaultPoint.value?.latitude || 0);
  const lon = Number(selectedFaultPoint.value?.longitude || 0);
  const zoom = 19;

  return `https://www.openstreetmap.org/?mlat=${encodeURIComponent(
    lat,
  )}&mlon=${encodeURIComponent(lon)}#map=${zoom}/${encodeURIComponent(
    lat,
  )}/${encodeURIComponent(lon)}`;
});

function clearFaultPointSelection() {
  selectedFaultPoint.value = null;
  faultPointResults.value = [];
  faultPointSearched.value = false;
}

function clearFaultPointResults() {
  faultPointResults.value = [];
  faultPointSearched.value = false;
}

async function handleFaultPointCategoryChange() {
  selectedFaultPoint.value = null;
  faultPointSearch.value = "";
  clearFaultPointResults();

  if (isCustomerPortal.value) {
    await searchFaultPoints();
  }
}

function selectFaultPoint(row: any) {
  selectedFaultPoint.value = row;
  faultPointResults.value = [];
  faultPointSearched.value = false;
}

async function searchFaultPoints() {
  faultPointLoading.value = true;
  faultPointSearched.value = true;

  try {
    const rows = await call(
      "telephony.customer_location_lookup.search_customer_fault_points",
      {
        txt: faultPointSearch.value,
        category: faultPointCategory.value,
        page_len: 64,
      },
    );

    faultPointResults.value = rows || [];
  } finally {
    faultPointLoading.value = false;
  }
}

watch(
  isCustomerPortal,
  async (isPortal) => {
    if (!isPortal) {
      return;
    }

    await searchFaultPoints();
  },
  { immediate: true },
);

function selectedFaultPointFields() {
  if (!isCustomerPortal.value || !selectedFaultPoint.value?.name) {
    return {};
  }

  if (selectedFaultPointIsNonPoint.value) {
    return {
      custom_fault_asset: selectedFaultPoint.value.name,
      custom_fault_category: faultPointCategory.value,
    };
  }

  return {
    custom_site: selectedFaultPoint.value.name,
    custom_fault_asset: selectedFaultPoint.value.name,
    custom_fault_category: faultPointCategory.value,
  };
}

const ticket = createResource({
  url: "helpdesk.helpdesk.doctype.hd_ticket.api.new",
  debounce: 300,
  makeParams: () => ({
    doc: {
      description: description.value,
      subject: subject.value,
      template: props.templateId,
      ...templateFields,
      ...selectedFaultPointFields(),
    },
    attachments: attachments.value,
  }),
  validate: (params) => {
    const fields = visibleFields.value?.filter((f) => f.required) || [];
    const toVerify = [...fields, "subject", "description"];
    for (const field of toVerify) {
      if (!params.doc[field.fieldname || field]) {
        return `${field.label || field} is required`;
      }
    }
  },
  onSuccess: (data) => {
    router.push({
      name: isCustomerPortal.value ? "TicketCustomer" : "TicketAgent",
      params: {
        ticketId: data.name,
      },
    });
    if (isManager) {
      updateOnboardingStep("create_first_ticket", true, false, () =>
        localStorage.setItem("firstTicket", data.name),
      );
    }
    // only capture telemetry for customer portal
    if (isCustomerPortal.value) {
      capture("new_ticket_submitted", {
        data: {
          user: userID,
          ticketID: data.name,
          subject: subject.value,
          description: description.value,
          customFields: templateFields,
        },
      });
    }
  },
});

function sanitize(html: string) {
  return sanitizeHtml(html, {
    allowedTags: sanitizeHtml.defaults.allowedTags.concat(["img"]),
  });
}

const breadcrumbs = computed(() => {
  const items = [
    {
      label: __("Tickets"),
      route: {
        name: isCustomerPortal.value ? "TicketsCustomer" : "TicketsAgent",
      },
    },
    {
      label: __("New Ticket"),
      route: {
        name: "TicketNew",
      },
    },
  ];
  return items;
});

usePageMeta(() => ({
  title: __("New Ticket"),
}));

onMounted(() => {
  capture("new_ticket_page", {
    data: {
      user: userID,
    },
  });
});
</script>
