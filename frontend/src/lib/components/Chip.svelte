<script lang="ts">
	let {
		label,
		active = false,
		onclick,
		removable = false
	}: {
		label: string;
		active?: boolean;
		onclick?: () => void;
		removable?: boolean;
	} = $props();
</script>

<button
	class="cursor-pointer rounded-full border px-2.5 py-1 text-xs tracking-wide {active
		? 'border-amber-soft-border bg-amber-soft-bg text-amber-soft-fg'
		: 'border-border-strong text-muted hover:text-ink hover:border-border-hover'}"
	{onclick}
>
	{label}{#if removable}<span class="ml-1">×</span>{/if}
</button>
