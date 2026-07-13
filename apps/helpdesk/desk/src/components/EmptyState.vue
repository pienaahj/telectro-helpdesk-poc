<template>
  <div class="flex h-full items-center justify-center">
    <div
      class="flex flex-col items-center gap-3 text-xl font-medium text-ink-gray-4"
    >
      <!-- Icon -->
      <component v-if="icon" :is="icon" class="h-10 w-10" />

      <!-- Title -->
      <span>{{ title }}</span>

      <!-- Optional action -->
      <Button
        v-if="showAction"
        label="Create"
        @click="emit('emptyStateAction')"
        variant="subtle"
      >
        <template #prefix>
          <FeatherIcon name="plus" class="h-4" />
        </template>
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { VNode } from "vue";

interface Props {
  title: string;
  icon?: VNode | string;
  showAction?: boolean;
}

withDefaults(defineProps<Props>(), {
  title: "No Data Found",
  icon: "",
  showAction: true,
});

const emit = defineEmits(["emptyStateAction"]);
</script>

<style lang="scss" scoped></style>
