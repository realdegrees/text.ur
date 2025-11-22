/**
 * Represents a PDF annotation with text selection and bounding boxes
 */
export interface Annotation {
	text: string;
	boundingBoxes: BoundingBox[];
	color: string;
}

/**
 * Represents a bounding box for text selection in normalized coordinates relative to the page (0-1)
 */
export interface BoundingBox {
	pageNumber: number;
	x: number;
	y: number;
	width: number;
	height: number;
}

/**
 * Type guard to check if an unknown object is a valid Annotation
 */
export function isAnnotation(obj: unknown): obj is Annotation {
	if (!obj || typeof obj !== 'object') return false;
	const annotation = obj as Record<string, unknown>;
	return (
		typeof annotation.text === 'string' &&
		Array.isArray(annotation.boundingBoxes) &&
		annotation.boundingBoxes.length > 0 &&
		typeof annotation.color === 'string'
	);
}

/**
 * Safely parse an annotation from an untyped object, providing defaults for missing fields
 */
export function parseAnnotation(obj: unknown): Annotation | null {
	if (!obj || typeof obj !== 'object') return null;
	const raw = obj as Record<string, unknown>;

	if (!Array.isArray(raw.boundingBoxes) || raw.boundingBoxes.length === 0) {
		return null;
	}

	return {
		text: typeof raw.text === 'string' ? raw.text : '',
		boundingBoxes: raw.boundingBoxes as BoundingBox[],
		color: typeof raw.color === 'string' ? raw.color : 'rgba(255, 235, 59, 0.4)'
	};
}