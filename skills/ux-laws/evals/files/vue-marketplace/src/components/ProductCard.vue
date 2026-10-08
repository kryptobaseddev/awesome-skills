<script setup lang="ts">
defineProps<{ item: any }>()
</script>
<template>
  <div class="productcard" style="border-radius: 14px; padding: 12px">
    <img :src="item.image" />
    <h3>{{ item.title }}</h3>
    <span style="color:#6d28d9">{{ item.price }}</span>
    <button>View</button>
  </div>
</template>
