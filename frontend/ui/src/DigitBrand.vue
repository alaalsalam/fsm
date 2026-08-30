<script setup lang="ts">
withDefaults(
	defineProps<{
		tone?: "light" | "dark";
		compact?: boolean;
		productAr?: string;
		productEn?: string;
		locale?: "ar" | "en";
	}>(),
	{
		tone: "light",
		compact: false,
		productAr: "التشغيل والصيانة",
		productEn: "Operations & Maintenance",
		locale: "ar",
	},
);
</script>

<template>
	<div
		class="digit-brand"
		:class="[`digit-brand--${tone}`, { 'digit-brand--compact': compact }]"
		aria-label="DIGIT Operations & Maintenance"
	>
		<svg
			class="digit-brand__wordmark"
			viewBox="0 0 378 96"
			role="img"
			aria-hidden="true"
			direction="ltr"
		>
			<g transform="translate(8 8)">
				<rect x="0" y="14" width="32" height="10" rx="5" fill="currentColor" />
				<rect x="37" y="14" width="15" height="10" rx="4" fill="#34D399" />
				<rect x="0" y="32" width="52" height="10" rx="5" fill="currentColor" />
				<rect x="0" y="50" width="40" height="10" rx="5" fill="currentColor" />
			</g>
			<text
				x="82"
				y="68"
				font-family="Archivo, Arial, sans-serif"
				font-size="64"
				font-weight="800"
				letter-spacing="1"
				fill="currentColor"
				direction="ltr"
			>
				DIGIT
			</text>
		</svg>
		<span v-if="!compact" class="digit-brand__product">
			{{ locale === "ar" ? productAr : productEn }}
		</span>
	</div>
</template>

<style scoped>
.digit-brand {
	display: inline-flex;
	min-width: 0;
	align-items: center;
	gap: 0.75rem;
	color: #f4f3ee;
}

.digit-brand--dark {
	color: #0b1f17;
}

.digit-brand__wordmark {
	display: block;
	width: 8.75rem;
	height: auto;
	flex: none;
	direction: ltr;
}

.digit-brand__product {
	border-inline-start: 1px solid color-mix(in srgb, currentColor 28%, transparent);
	padding-inline-start: 0.75rem;
	font-family: var(--kl-font-ui);
	font-size: 0.75rem;
	font-weight: 600;
	line-height: 1.35;
	white-space: nowrap;
	opacity: 0.78;
}

.digit-brand--compact .digit-brand__wordmark {
	width: 6.75rem;
}

@media (max-width: 420px) {
	.digit-brand__wordmark {
		width: 6.75rem;
	}

	.digit-brand__product {
		display: none;
	}
}
</style>
