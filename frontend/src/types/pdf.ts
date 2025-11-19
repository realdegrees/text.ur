/**
 * Represents a text item in the PDF text layer
 */
export interface TextLayerItem {
	text: string;
	left: number;
	top: number;
	fontSize: number;
	fontFamily: string;
	angle: number;
	id: string;
}

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
 * (Same as BoundingBox but semantically represents scaled/absolute coordinates)
 */
export type ScaledBoundingBox = BoundingBox;

