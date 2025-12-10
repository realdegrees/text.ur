/**
 * Reactive screen size detection utilities
 * Returns reactive state for screen size detection
 */

export type ScreenSize = 'mobile' | 'tablet' | 'desktop';

export interface ScreenState {
	size: ScreenSize;
	isMobile: boolean;
	isTablet: boolean;
	isDesktop: boolean;
	width: number;
	height: number;
}

const BREAKPOINTS = {
	mobile: 768, // < 768px
	tablet: 1024 // < 1024px
} as const;

function getScreenSize(width: number): ScreenSize {
	if (width < BREAKPOINTS.mobile) return 'mobile';
	if (width < BREAKPOINTS.tablet) return 'tablet';
	return 'desktop';
}

/**
 * Creates a reactive screen state object that updates on resize
 * Note: This should be called within a component context to ensure proper cleanup
 */
export function createScreenState(): ScreenState {
	let width = $state(typeof window !== 'undefined' ? window.innerWidth : 1024);
	let height = $state(typeof window !== 'undefined' ? window.innerHeight : 768);

	const size = $derived(getScreenSize(width));
	const isMobile = $derived(size === 'mobile');
	const isTablet = $derived(size === 'tablet');
	const isDesktop = $derived(size === 'desktop');

	// Set up resize listener with automatic cleanup via $effect
	$effect(() => {
		if (typeof window === 'undefined') return;

		const handleResize = () => {
			width = window.innerWidth;
			height = window.innerHeight;
		};

		window.addEventListener('resize', handleResize);

		return () => {
			window.removeEventListener('resize', handleResize);
		};
	});

	return {
		get size() {
			return size;
		},
		get isMobile() {
			return isMobile;
		},
		get isTablet() {
			return isTablet;
		},
		get isDesktop() {
			return isDesktop;
		},
		get width() {
			return width;
		},
		get height() {
			return height;
		}
	};
}

/**
 * Detect if device has hover capability (typically desktop)
 * Returns false on touch-only devices
 */
export function hasHoverCapability(): boolean {
	if (typeof window === 'undefined') return true;
	return window.matchMedia('(hover: hover) and (pointer: fine)').matches;
}
