async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
	const res = await fetch(`/api${path}`, {
		method,
		headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
		body: body !== undefined ? JSON.stringify(body) : undefined
	});
	if (!res.ok) {
		let message = `${method} ${path} failed with ${res.status}`;
		try {
			const data = await res.json();
			if (data?.error) message = data.error;
		} catch {
			// response wasn't JSON; keep the generic message
		}
		throw new Error(message);
	}
	if (res.status === 204) return undefined as T;
	return res.json() as Promise<T>;
}

export const apiGet = <T>(path: string) => request<T>('GET', path);
export const apiPost = <T>(path: string, body?: unknown) => request<T>('POST', path, body ?? {});
export const apiPut = <T>(path: string, body?: unknown) => request<T>('PUT', path, body ?? {});
export const apiDelete = <T>(path: string) => request<T>('DELETE', path);
