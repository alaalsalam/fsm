import type { CapacitorConfig } from "@capacitor/cli";

// Native chrome mirrors the canonical DIGIT identity.
const config: CapacitorConfig = {
	appId: "com.digit.fsm",
	appName: "DIGIT Operations & Maintenance",
	webDir: "dist",
	server: {
		androidScheme: "https",
		iosScheme: "https",
	},
	plugins: {
		SplashScreen: {
			launchAutoHide: false,
			backgroundColor: "#064E3B",
			showSpinner: false,
			splashFullScreen: true,
			splashImmersive: true,
		},
		StatusBar: {
			style: "LIGHT",
			backgroundColor: "#064E3B",
		},
		Keyboard: {
			resize: "body",
		},
		PushNotifications: {
			presentationOptions: ["badge", "sound", "alert"],
		},
		LocalNotifications: {
			smallIcon: "ic_stat_notification",
			iconColor: "#0A8754",
		},
	},
	android: {
		backgroundColor: "#064E3B",
	},
	ios: {
		backgroundColor: "#064E3B",
		contentInset: "automatic",
	},
};

export default config;
