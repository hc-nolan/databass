<script lang="ts">
	import type { Fact } from '$lib/types';
	import { toneTextClass } from '$lib/format';

	let { facts }: { facts: Fact[] } = $props();
</script>

<div class="border-border bg-border flex flex-wrap gap-px overflow-hidden rounded-lg border">
	{#each facts as f (f.label)}
		<div class="bg-panel flex min-w-[128px] flex-1 flex-col gap-0.5 px-3.5 py-3">
			<span class="text-2xs text-muted tracking-wider">{f.label}</span>
			<span class="text-lg font-semibold tracking-tight {toneTextClass(f.tone)}">{f.value}</span>
		</div>
	{/each}
</div>
