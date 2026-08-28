// DIGIT Field Service design tokens — generated from tokens.json. Do not edit by hand.
export const tokens = {
	brand: {
		"50": "#E6F3EC",
		"100": "#C7E5D5",
		"300": "#34D399",
		"500": "#0A8754",
		"700": "#064E3B",
		"900": "#032D23",
	},
	status: {
		success: "#067647",
		warning: "#B54708",
		danger: "#B42318",
		info: "#175CD3",
	},
	surface: {
		light: {
			bg: "#F4F3EE",
			"bg-subtle": "#F7F9F7",
			surface: "#FFFFFF",
			border: "#D6DFDA",
			text: "#0B1F17",
			"text-muted": "#71807A",
			brand: "#0A8754",
		},
		dark: {
			bg: "#0C100E",
			"bg-subtle": "#161B18",
			surface: "#1C2320",
			border: "#3E4B45",
			text: "#EEF3F1",
			"text-muted": "#869389",
			brand: "#34D399",
		},
	},
	font: {
		ui: "'IBM Plex Sans Arabic', 'Archivo', Tahoma, system-ui, sans-serif",
		mono: "'Archivo', 'IBM Plex Sans Arabic', system-ui, sans-serif",
		currency: "'SaudiRiyal', 'IBM Plex Sans Arabic', system-ui, sans-serif",
		size: {
			xs: "12px",
			sm: "14px",
			base: "16px",
			lg: "18px",
			xl: "22px",
			"2xl": "28px",
			"3xl": "34px",
		},
	},
	radius: {
		sm: "8px",
		md: "12px",
		lg: "16px",
		full: "999px",
	},
	command: {
		bg: "#06402F",
		"bg-2": "#032D23",
		glow: "rgba(52,211,153,0.16)",
		glass: "rgba(255,255,255,0.065)",
		"glass-strong": "rgba(255,255,255,0.085)",
		"glass-border": "rgba(255,255,255,0.10)",
		"glass-border-strong": "rgba(255,255,255,0.18)",
		text: "#F4F3EE",
		"text-muted": "#B8C8C0",
		brand: "#34D399",
		blur: "14px",
	},
	gradient: {
		brand: "linear-gradient(135deg, #34D399 0%, #0A8754 52%, #064E3B 100%)",
		"brand-soft":
			"linear-gradient(135deg, rgba(52,211,153,0.18) 0%, rgba(10,135,84,0.06) 100%)",
		surface: "linear-gradient(160deg, rgba(255,255,255,0.09) 0%, rgba(255,255,255,0.015) 100%)",
	},
	touchMin: "44px",
} as const;
export type Tokens = typeof tokens;
