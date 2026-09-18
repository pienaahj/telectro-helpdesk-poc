<template>
  <div class="flex min-h-screen flex-col bg-[#fbf8f2]">
    <LayoutHeader>
      <template #left-header>
        <div class="flex min-w-0 items-center gap-1 text-lg font-medium">
          <RouterLink
            :to="{ name: 'TicketsCustomer' }"
            class="min-w-0 truncate text-ink-gray-6"
          >
            {{ __("Support Requests") }}
          </RouterLink>

          <span class="shrink-0 text-ink-gray-5">/</span>

          <RouterLink
            :to="{
              name: 'TicketCustomer',
              params: { ticketId: props.ticketId },
            }"
            class="shrink-0 text-ink-gray-6"
          >
            #{{ props.ticketId }}
          </RouterLink>

          <span class="shrink-0 text-ink-gray-5">/</span>

          <span class="shrink-0 text-ink-gray-9">
            {{ __("Map") }}
          </span>
        </div>
      </template>
    </LayoutHeader>

    <main class="mx-auto w-full max-w-5xl flex-1 px-6 py-6 md:px-10">
      <div
        class="overflow-hidden rounded-2xl border border-[#d6c7a8] bg-[#fffdf8] shadow-sm"
      >
        <div class="h-1 bg-[#b79a55]" />

        <div class="space-y-6 p-5 md:p-6">
          <div>
            <div class="text-sm uppercase tracking-[0.18em] text-[#757c65]">
              {{ __("Boschendal Service Desk") }}
            </div>

            <h1 class="mt-1 text-2xl font-semibold text-gray-900">
              {{ __("Fault location") }}
            </h1>

            <p class="mt-1 text-sm text-gray-600">
              {{ __("Support request") }} #{{ props.ticketId }}
            </p>
          </div>

          <div v-if="loading" class="text-base text-gray-600">
            {{ __("Loading location…") }}
          </div>

          <div
            v-else-if="errorMessage"
            class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
          >
            {{ errorMessage }}
          </div>

          <div
            v-else
            class="grid gap-4 rounded-xl border border-[#e5ded2] bg-white p-4 md:grid-cols-2"
          >
            <div>
              <div class="text-xs font-medium uppercase text-gray-500">
                {{ __("Campus") }}
              </div>
              <div class="mt-1 text-base font-medium text-gray-900">
                {{ locationContext.campus || "—" }}
              </div>
            </div>

            <div>
              <div class="text-xs font-medium uppercase text-gray-500">
                {{ __("Category") }}
              </div>
              <div class="mt-1 text-base font-medium text-gray-900">
                {{ locationContext.category || "—" }}
              </div>
            </div>

            <div>
              <div class="text-xs font-medium uppercase text-gray-500">
                {{ __("Fault Point") }}
              </div>
              <div class="mt-1 text-base font-medium text-gray-900">
                {{ locationContext.fault_point || "—" }}
              </div>
            </div>

            <div>
              <div class="text-xs font-medium uppercase text-gray-500">
                {{ __("Affected Equipment") }}
              </div>
              <div class="mt-1 text-base font-medium text-gray-900">
                {{ locationContext.affected_equipment || "—" }}
              </div>
            </div>

            <div>
              <div class="text-xs font-medium uppercase text-gray-500">
                {{ __("Equipment Ref") }}
              </div>
              <div class="mt-1 text-base font-medium text-gray-900">
                {{ locationContext.equipment_ref || "—" }}
              </div>
            </div>

            <div>
              <div class="text-xs font-medium uppercase text-gray-500">
                {{ __("Latitude") }}
              </div>
              <div class="mt-1 break-all text-base font-medium text-gray-900">
                {{ locationContext.latitude ?? "—" }}
              </div>
            </div>

            <div>
              <div class="text-xs font-medium uppercase text-gray-500">
                {{ __("Longitude") }}
              </div>
              <div class="mt-1 break-all text-base font-medium text-gray-900">
                {{ locationContext.longitude ?? "—" }}
              </div>
            </div>
          </div>

            <div v-if="!loading && !errorMessage">
                <div
                    v-if="hasCoordinates"
                    ref="mapContainer"
                    class="h-[420px] w-full overflow-hidden rounded-xl border border-[#d6c7a8] md:h-[500px]"
                />

                <div
                    v-else
                    class="rounded-xl border border-dashed border-[#d6c7a8] bg-[#fbf8f2] p-6 text-center text-sm text-gray-600"
                >
                    {{ __("No map coordinates are available for this fault point.") }}
                </div>
            </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";
import { call } from "frappe-ui";
import * as L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  computed,
  nextTick,
  onUnmounted,
  ref,
  watch,
} from "vue";

interface CustomerLocationContext {
  ticket?: string;
  customer?: string;
  campus?: string;
  category?: string;
  service_area?: string;
  affected_equipment?: string;
  affected_equipment_id?: string;
  affected_equipment_type?: string;
  affected_equipment_manufacturer?: string;
  affected_equipment_model?: string;
  equipment_ref?: string;
  fault_point?: string;
  fault_point_id?: string;
  parent_location?: string;
  latitude?: number | string | null;
  longitude?: number | string | null;
  geometry_type?: string;
}

const ESRI_IMAGERY_TILE_URL =
  "https://ibasemaps-api.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

const ESRI_IMAGERY_ATTRIBUTION =
  "Source: Esri, Vantor, GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN, and the GIS User Community";

const ESRI_API_KEY = String(
  import.meta.env.VITE_ESRI_API_KEY || "",
).trim();

interface P {
  ticketId: string;
}

const props = defineProps<P>();

const locationContext = ref<CustomerLocationContext>({});
const loading = ref(false);
const errorMessage = ref("");

const mapContainer = ref<HTMLElement | null>(null);

let mapInstance: ReturnType<typeof L.map> | null = null;

const hasCoordinates = computed(() => {
  const latitude = Number(locationContext.value.latitude);
  const longitude = Number(locationContext.value.longitude);

  return Number.isFinite(latitude) && Number.isFinite(longitude);
});

function destroyMap() {
  if (!mapInstance) {
    return;
  }

  mapInstance.remove();
  mapInstance = null;
}

async function renderMap() {
  destroyMap();

  if (!hasCoordinates.value) {
    return;
  }

  await nextTick();

  if (!mapContainer.value) {
    return;
  }

  const latitude = Number(locationContext.value.latitude);
  const longitude = Number(locationContext.value.longitude);

  if (!ESRI_API_KEY) {
    errorMessage.value = __("Aerial map configuration is unavailable.");
    return;
    }

  mapInstance = L.map(mapContainer.value).setView(
    [latitude, longitude],
    19,
  );

  L.tileLayer(
    `${ESRI_IMAGERY_TILE_URL}?token=${encodeURIComponent(ESRI_API_KEY)}`,
    {
        attribution: ESRI_IMAGERY_ATTRIBUTION,
    },
  ).addTo(mapInstance);

  L.circleMarker([latitude, longitude])
    .addTo(mapInstance)
    .bindTooltip(locationContext.value.fault_point || __("Fault Point"));

  mapInstance.invalidateSize();
}

async function loadCustomerLocationContext(ticketName: string) {
  loading.value = true;
  errorMessage.value = "";
  locationContext.value = {};

  try {
    locationContext.value =
      (await call(
        "telephony.customer_location_lookup.get_customer_ticket_location_context",
        {
          ticket_name: String(ticketName),
        },
      )) || {};
  } catch (error) {
    console.error("Failed to load customer location context", error);
    errorMessage.value = __("Unable to load this ticket location.");
  } finally {
    loading.value = false;

    if (!errorMessage.value) {
        await renderMap();
    }
  }
}

watch(
  () => props.ticketId,
  (ticketId) => {
    if (ticketId) {
      loadCustomerLocationContext(String(ticketId));
    }
  },
  { immediate: true },
);

onUnmounted(() => {
  destroyMap();
});

</script>
