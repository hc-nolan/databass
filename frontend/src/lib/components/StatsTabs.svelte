<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';

	const tabs = [
		{ value: 'habits' as const, label: 'habits', href: '/stats' as const },
		{ value: 'explore' as const, label: 'explore', href: '/stats/explore' as const }
		, { value: 'listenbrainz' as const, label: 'listenbrainz', href: '/stats/listenbrainz' as const }
	];
	const active = $derived(page.url.pathname === '/stats/explore' ? 'explore' : page.url.pathname === '/stats/listenbrainz' ? 'listenbrainz' : 'habits');
</script>

<div class="flex gap-1 rounded-lg border border-border bg-panel p-1">
	{#each tabs as t (t.value)}
		<button
			class="cursor-pointer rounded-md px-3.5 py-1.5 text-sm font-semibold {active === t.value
				? 'bg-amber text-on-amber'
				: 'text-muted hover:text-ink'}"
			onclick={() => goto(resolve(t.href))}
		>
			{t.label}
		</button>
	{/each}
</div>
