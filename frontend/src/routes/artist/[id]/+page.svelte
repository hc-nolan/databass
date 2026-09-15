<script lang="ts">
	import { page } from '$app/state';
	import DetailView from '$lib/components/DetailView.svelte';

	const id = $derived(Number(page.params.id));
</script>

<DetailView kind="artist" {id} />
