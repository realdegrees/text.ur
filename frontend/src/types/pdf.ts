/**
 * Represents a PDF annotation with text selection and bounding boxes
 */
export interface Annotation {
	pageNumber: number;
	text: string;
	boundingBoxes: BoundingBox[];
	color: string;
	timestamp: number;
}

/**
 * Represents a bounding box for text selection in normalized coordinates (0-1)
 */
export interface BoundingBox {
	x: number;
	y: number;
	width: number;
	height: number;
}

/**
 * Represents a bounding box in pixel coordinates
 */
export interface ScaledBoundingBox extends BoundingBox {}
