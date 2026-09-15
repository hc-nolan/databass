<script lang="ts">
	let {
		options,
		value,
		onchange
	}: {
		options: { value: string; label: string }[];
		value: string;
		onchange: (value: string) => void;
	} = $props();
</script>

<div class="border-border bg-panel flex gap-1 rounded-lg border p-1">
	{#each options as opt (opt.value)}
		<button
			class="cursor-pointer rounded-md px-3.5 py-1.5 text-sm font-semibold {value === opt.value
				? 'bg-amber text-on-amber'
				: 'text-muted hover:text-ink'}"
			onclick={() => onchange(opt.value)}
		>
			{opt.label}
		</button>
	{/each}
</div>
