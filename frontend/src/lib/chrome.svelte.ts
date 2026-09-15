import type { Snippet } from 'svelte';

export const headerState: { counter: Snippet | null } = $state({ counter: null });
