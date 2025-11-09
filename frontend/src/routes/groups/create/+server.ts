import { type RequestHandler, error, json } from "@sveltejs/kit";

export const POST: RequestHandler = async ({ request, fetch }) => {
	const body = await request.json();
	
	const response = await fetch("/api/groups", {
		method: "POST",
		headers: {
			"Content-Type": "application/json"
		},
		body: JSON.stringify(body)
	});

	if (!response.ok) {
		const errorData = await response.json().catch(() => ({ detail: "Failed to create group" }));
		error(response.status, errorData.detail || "Failed to create group");
	}

	const data = await response.json();
	return json(data);
};
