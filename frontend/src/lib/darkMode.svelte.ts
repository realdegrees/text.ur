import { browser } from "$app/environment";

function getThemeFromCookie(): string | null {
	if (!browser) return null;
	const match = document.cookie.match(/(?:^|;\s*)theme=([^;]*)/);
	return match ? match[1] : null;
}

function hasThemeCookie(): boolean {
	if (!browser) return false;
	return document.cookie.includes("theme=");
}

function getInitialTheme(): boolean {
	if (!browser) return false;
	return getThemeFromCookie() === "dark" || 
		(!hasThemeCookie() && window.matchMedia("(prefers-color-scheme: dark)").matches);
}

const createDarkMode = () => {
	let isDark = $state(getInitialTheme());

	return {
		get enabled(): boolean {
			return isDark;
		},
		set enabled(value: boolean) {
			if (!browser) return;
			
			isDark = value;
			this.apply();
			
			if (value) {
				document.cookie = "theme=dark; path=/;";
			} else {
				document.cookie = "theme=light; path=/;";
			}
		},
		disable() {
			if (!browser) return;
			
			isDark = false;
			this.apply();
			document.cookie = "theme=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
		},
		apply() {
			if (!browser) return;
			document.documentElement.classList.toggle("dark", isDark);
		},
	};
};

export default createDarkMode();
