<script setup lang="ts">
defineProps<{ name: string }>();
</script>

<template>
	<svg
		viewBox="0 0 24 24"
		fill="none"
		stroke="currentColor"
		stroke-width="1.8"
		stroke-linecap="round"
		stroke-linejoin="round"
		aria-hidden="true"
	>
		<template v-if="name === 'operations'">
			<path d="M4 13a8 8 0 1 1 16 0M12 13l4-4M5 18h14" />
		</template>
		<template v-else-if="name === 'dispatch'">
			<rect x="3" y="3" width="7" height="9" rx="1.5" />
			<rect x="14" y="3" width="7" height="5" rx="1.5" />
			<rect x="14" y="12" width="7" height="9" rx="1.5" />
			<rect x="3" y="16" width="7" height="5" rx="1.5" />
		</template>
		<template v-else-if="name === 'requests'">
			<path d="M4 4h16v14H4zM4 14h4l2 3h4l2-3h4" />
		</template>
		<template v-else-if="name === 'jobs'">
			<rect x="8" y="2" width="8" height="4" rx="1" />
			<path d="M16 4h2a2 2 0 0 1 2 2v14H4V6a2 2 0 0 1 2-2h2M9 12h6M9 16h6" />
		</template>
		<template v-else-if="name === 'visits'">
			<path d="M20 10c0 4.5-8 11-8 11S4 14.5 4 10a8 8 0 1 1 16 0Z" />
			<circle cx="12" cy="10" r="2.5" />
		</template>
		<template v-else-if="name === 'exceptions'">
			<path d="m12 3 9 17H3L12 3ZM12 9v4M12 17h.01" />
		</template>
		<template v-else-if="name === 'after-sales'">
			<path d="M4 7h10M18 7h2M4 17h2M10 17h10" />
			<circle cx="16" cy="7" r="2" />
			<circle cx="8" cy="17" r="2" />
		</template>
		<template v-else-if="name === 'equipment'">
			<path d="m3 7 9-4 9 4-9 4-9-4ZM3 7v10l9 4 9-4V7M12 11v10" />
		</template>
		<template v-else-if="name === 'customer-360'">
			<circle cx="9" cy="8" r="3" />
			<path d="M3 20a6 6 0 0 1 12 0M16 4a3 3 0 0 1 0 6M21 20a6 6 0 0 0-5-6" />
		</template>
		<template v-else-if="name === 'sites'">
			<path d="M4 21V5l8-3v19M12 8h8v13M2 21h20M7 7h2M7 11h2M7 15h2M15 12h2M15 16h2" />
		</template>
		<template v-else-if="name === 'contracts'">
			<path d="M6 3h9l4 4v14H6zM15 3v5h4M9 13h7M9 17h5" />
		</template>
		<template v-else-if="name === 'maintenance'">
			<path d="M7 3v3M17 3v3M4 9h16M5 5h14v16H5zM9 15l2 2 4-5" />
		</template>
		<template v-else-if="name === 'equipment-locations'">
			<path d="M20 10c0 4.5-8 11-8 11S4 14.5 4 10a8 8 0 1 1 16 0ZM9 10l3-2 3 2-3 2-3-2Z" />
		</template>
		<template v-else-if="name === 'inventory'">
			<path d="M3 8h18v12H3zM7 8V4h10v4M9 13h6" />
		</template>
		<template v-else-if="name === 'returns'">
			<path d="M3 7h13a4 4 0 0 1 0 8H7M7 11l-4 4 4 4" />
		</template>
		<template v-else-if="name === 'subcontractors'">
			<path
				d="m8 12 3 3a2 2 0 0 0 3-3l-2-2M12 10l2-2a3 3 0 0 1 4 0l3 3-7 7a3 3 0 0 1-4 0l-7-7 3-3a3 3 0 0 1 4 0l1 1"
			/>
		</template>
		<template v-else-if="name === 'analytics'">
			<path d="M3 3v18h18M7 16v-4M12 16V8M17 16V5" />
		</template>
		<template v-else-if="name === 'integrations'">
			<circle cx="6" cy="12" r="2.5" />
			<circle cx="18" cy="6" r="2.5" />
			<circle cx="18" cy="18" r="2.5" />
			<path d="m8.2 10.8 7.6-3.6M8.2 13.2l7.6 3.6" />
		</template>
		<template v-else>
			<circle cx="12" cy="8" r="3.5" />
			<path d="M5 20a7 7 0 0 1 14 0" />
		</template>
	</svg>
</template>
