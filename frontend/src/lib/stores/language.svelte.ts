import { browser } from '$app/environment';
import { locales, isLocale, baseLocale } from '$i18n/i18n-util';
import type { Locales } from '$i18n/i18n-types';

function getLocaleFromCookie(): Locales | null {
	if (!browser) return null;
	const match = document.cookie.match(/(?:^|;\s*)locale=([^;]*)/);
	const cookieLocale = match ? match[1] : null;
	return cookieLocale && isLocale(cookieLocale) ? cookieLocale : null;
}

function getInitialLocale(): Locales {
	if (!browser) return baseLocale;
	return getLocaleFromCookie() || baseLocale;
}

const createLanguage = () => {
	let currentLocale = $state(getInitialLocale());

	return {
		get locale(): Locales {
			return currentLocale;
		},
		
		get availableLocales(): Locales[] {
			return locales;
		},
		
		setLocale(locale: Locales) {
			if (!browser || !isLocale(locale)) return;

			currentLocale = locale;
			
			// Set the locale cookie (same pattern as darkMode)
			document.cookie = `locale=${locale}; path=/; max-age=${60 * 60 * 24 * 365}`;
		},
		
		clearLocale() {
			if (!browser) return;

			currentLocale = baseLocale;
			document.cookie = 'locale=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
		}
	};
};

export default createLanguage();