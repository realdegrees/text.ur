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

// ============================================================================
// Pointer & Platform Detection
// ============================================================================

type PointerType = 'mouse' | 'touch' | 'pen';

/**
 * Detect the current platform from the user agent string.
 * Used to determine whether native text selection handles (teardrops)
 * are reliably provided by the OS.
 */
function detectPlatform(): { isIOS: boolean; isAndroid: boolean } {
	if (typeof navigator === 'undefined') {
		return { isIOS: false, isAndroid: false };
	}
	const ua = navigator.userAgent;
	// iPadOS 13+ reports as Macintosh in UA; detect via touch points
	const isIOS =
		/iPad|iPhone|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
	const isAndroid = /Android/.test(ua);
	return { isIOS, isAndroid };
}

const platform = detectPlatform();

/**
 * Whether the current platform reliably provides native text selection
 * handles (teardrops). True only for iOS and Android where native
 * handles are guaranteed by the OS. False for Windows touch, ChromeOS,
 * and other platforms where native handle behavior is inconsistent.
 */
const reliableNativeHandles = platform.isIOS || platform.isAndroid;

// Default pointer type: use media query as initial heuristic.
// Touch-primary devices start as 'touch', others as 'mouse'.
// Updated on every pointerdown event to reflect actual input method.
const initialPointerType: PointerType =
	typeof window !== 'undefined' && !window.matchMedia('(hover: hover) and (pointer: fine)').matches
		? 'touch'
		: 'mouse';

let lastPointerType = $state<PointerType>(initialPointerType);

// Track actual pointer type from user interactions
if (typeof window !== 'undefined') {
	window.addEventListener(
		'pointerdown',
		(e: PointerEvent) => {
			const pt = e.pointerType as PointerType;
			if (pt !== lastPointerType) {
				lastPointerType = pt;
			}
		},
		{ capture: true, passive: true }
	);
}

/**
 * Global reactive pointer and platform state singleton.
 *
 * Tracks the current input method (mouse/touch/pen) and platform
 * capabilities to determine how text selection handles should behave
 * across different devices.
 *
 * - iOS/Android touch: relies on native OS selection handles
 * - Desktop mouse/pen: shows custom handles
 * - Other touch platforms (Windows, ChromeOS): shows custom handles
 *   as fallback since native handles are not guaranteed
 *
 * @see frontend/README.md "Text Selection Handles" for documentation
 */
export const pointerState = {
	/** The most recent pointer type from the last pointerdown event. */
	get lastPointerType(): PointerType {
		return lastPointerType;
	},
	/** True when the user's last interaction was touch. */
	get isTouchInteraction(): boolean {
		return lastPointerType === 'touch';
	},
	/** True on platforms with reliable native selection handles. */
	get hasReliableNativeHandles(): boolean {
		return reliableNativeHandles;
	},
	/**
	 * True when custom selection handles should be displayed.
	 * Shows handles when using mouse/pen (no native handles), or
	 * when using touch on platforms without reliable native handles.
	 */
	get showCustomHandles(): boolean {
		return lastPointerType !== 'touch' || !reliableNativeHandles;
	},
	/** Detected platform info. */
	get platform(): { isIOS: boolean; isAndroid: boolean } {
		return platform;
	}
};
