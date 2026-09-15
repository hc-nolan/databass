<script lang="ts">
	let { mode = 'normal' }: { mode?: string } = $props();
</script>

<div
	class="border-border bg-panel text-muted pointer-events-none fixed bottom-3 left-3.5 rounded-sm border px-2.5 py-[3px] text-xs tracking-wider"
>
	{mode}
</div>
