import type { BreadcrumbItem } from '$types/breadcrumb';

/**
 * Optional override for the breadcrumbs shown in the Breadcrumb component.
 * When set, takes precedence over `$page.data.breadcrumbs`.
 * Pages that need dynamic breadcrumbs (e.g. tab-based) can set this
 * reactively and clear it on unmount.
 */
const createBreadcrumbOverride = () => {
	let items = $state<BreadcrumbItem[] | null>(null);

	return {
		get items() {
			return items;
		},
		set(value: BreadcrumbItem[] | null) {
			items = value;
		},
		clear() {
			items = null;
		}
	};
};

export const breadcrumbOverride = createBreadcrumbOverride();
