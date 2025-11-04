const darkMode = () => {
	$effect.root(() => {
		$effect(() => {
			document.documentElement.classList.toggle(
				"dark",
				getThemeFromCookie() === "dark" ||
					(!hasThemeCookie() && window.matchMedia("(prefers-color-scheme: dark)").matches)
			);
		});
	});

	return {
		get enabled(): boolean {
			return (
				getThemeFromCookie() === "dark" ||
				(!hasThemeCookie() && window.matchMedia("(prefers-color-scheme: dark)").matches)
			);
		},
		set enabled(value: boolean) {
			if (value) {
				document.cookie = "theme=dark";
			} else {
				document.cookie = "theme=light";
			}
		},
		disable() {
			document.cookie = "theme=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
		},
	};
}

function getThemeFromCookie(): string | null {
	const match = document.cookie.match(/(?:^|;\s*)theme=([^;]*)/);
	return match ? match[1] : null;
}

function hasThemeCookie(): boolean {
	return document.cookie.includes("theme=");
}

export default darkMode();
