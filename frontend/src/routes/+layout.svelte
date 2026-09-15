<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import Header from '$lib/components/Header.svelte';
	import ModePill from '$lib/components/ModePill.svelte';

	let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="min-h-screen">
	<Header />
	<div class="mx-auto max-w-[1440px]">
		{@render children()}
	</div>
	<ModePill />
</div>
