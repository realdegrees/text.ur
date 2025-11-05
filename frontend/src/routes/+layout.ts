import type { LayoutLoad } from './$types';
import { loadLocaleAsync } from '$i18n/i18n-util.async';
import { setLocale } from '$i18n/i18n-svelte';

export const load: LayoutLoad = async (event) => {
	const locale = event.data.locale;
	await loadLocaleAsync(locale);
	setLocale(locale);
	return event.data;
};
