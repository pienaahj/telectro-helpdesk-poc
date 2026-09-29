import { isCustomerPortal } from "@/utils";
import { createResource } from "frappe-ui";
import { computed, watch } from "vue";

export interface CustomerPortalProfile {
  customer: string;
  customer_name: string;
  service_desk_name: string;
  logo: string;
  primary_colour: string;
  accent_colour: string;
  foreground_colour: string;
}

const neutralProfile: CustomerPortalProfile = {
  customer: "",
  customer_name: "",
  service_desk_name: "Service Desk",
  logo: "",
  primary_colour: "",
  accent_colour: "",
  foreground_colour: "",
};

export const customerPortalProfileResource = createResource({
  url: "telephony.customer_location_lookup.get_customer_portal_profile",
  auto: false,
});

function ensureCustomerPortalProfile() {
  if (!isCustomerPortal.value) {
    return;
  }

  if (
    customerPortalProfileResource.data ||
    customerPortalProfileResource.loading
  ) {
    return;
  }

  customerPortalProfileResource.fetch();
}

export function useCustomerPortalProfile() {
  watch(
    () => isCustomerPortal.value,
    () => {
      ensureCustomerPortalProfile();
    },
    { immediate: true },
  );

  const profile = computed<CustomerPortalProfile>(() => ({
    ...neutralProfile,
    ...(customerPortalProfileResource.data || {}),
  }));

  return {
    profile,
    resource: customerPortalProfileResource,
  };
}
