import { browser } from '$app/environment';
import { Tween } from 'svelte/motion';
import { cubicOut } from 'svelte/easing';

function clamp(value: number): number {
	return Math.min(100, Math.max(0, Math.round(value)));
}

const createLoadingBar = () => {
	let isVisible = $state(false);
	// use a tweened store for smooth progress animation
	const progressTween = new Tween(0, {
		duration: 400,
		easing: cubicOut
	});

	let finishing = false;

	return {
		get visible(): boolean {
			return isVisible;
		},
		get progress(): number {
			return progressTween.current;
		},
		progressTween,

		set(value: number) {
			if (!browser) return;

			const v = clamp(value);
			if (v > 0 && v < 100) {
				isVisible = true;
				progressTween.set(v); // tween smoothly
			}
			if (v === 100 && !finishing) this.finish();
		},

		async finish() {
			if (!browser) return;

			finishing = true;
			try {
				isVisible = true;
				progressTween.set(100);
				await new Promise((r) => setTimeout(r, 300));
				isVisible = false;
				await new Promise((r) => setTimeout(r, 200));
				progressTween.set(0);
			} finally {
				finishing = false;
			}
		},

		one_shot(duration: number = 1000) {
			if (!browser) return;

			isVisible = true;
			progressTween.set(0);
			const start = performance.now();

			const animate = (now: number) => {
				const t = Math.min((now - start) / duration, 1);
				progressTween.set(t * 100);
				if (t < 1) requestAnimationFrame(animate);
				else this.finish();
			};
			requestAnimationFrame(animate);
		},

		reset() {
			if (!browser) return;
			progressTween.set(0);
			isVisible = false;
		}
	};
};

export const loadingBar = createLoadingBar();
