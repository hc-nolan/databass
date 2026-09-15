<script lang="ts">
	import { page } from '$app/state';
	import { headerState } from '$lib/chrome.svelte';

	const navItems = [
		{ label: 'home', href: '/' },
		{ label: 'new', href: '/new' },
		{ label: 'browse', href: '/browse/releases', matchPrefix: '/browse' },
		{ label: 'stats', href: '/stats' },
		{ label: 'goals', href: '/goals' }
	];

	function isActive(item: (typeof navItems)[number]): boolean {
		const path = page.url.pathname;
		if (item.matchPrefix) return path.startsWith(item.matchPrefix);
		return path === item.href;
	}
</script>

<header class="border-line flex flex-wrap items-baseline gap-x-7 gap-y-5 border-b px-7 py-5.5">
	<div class="flex items-baseline gap-2">
		<span class="text-xl font-extrabold tracking-tightest">databass</span>
		<span class="text-2xs text-muted tracking-wider">v0.7</span>
	</div>
	<nav class="mr-auto flex flex-wrap gap-0.5">
		{#each navItems as item (item.label)}
			<a
				href={item.href}
				class="rounded-full px-2.5 py-1 text-sm tracking-tight {isActive(item)
					? 'bg-hover text-ink'
					: 'text-muted hover:text-ink'}"
			>
				{item.label}
			</a>
		{/each}
	</nav>
	<div class="text-sm text-muted-2 flex items-center gap-2.5">
		{@render headerState.counter?.()}
	</div>
</header>
