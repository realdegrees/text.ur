function DarkMode() {
	$effect.root(() => {
		$effect(() => {
			document.documentElement.classList.toggle(
				'dark',
				localStorage.theme === 'dark' ||
					(!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)
			);
		});
	});

	return {
		get enabled(): boolean {
			return localStorage.theme === 'dark' ||
					(!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)
		},
		toggle() {
			localStorage.theme = localStorage.theme === 'dark' ? 'light' : 'dark';
		},
		disable() {
			localStorage.removeItem("theme");
		}
	};
}
export default DarkMode();
