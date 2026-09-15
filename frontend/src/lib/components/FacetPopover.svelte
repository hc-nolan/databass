<script lang="ts">
	import { Popover } from 'bits-ui';

	let {
		label,
		options,
		value,
		onchange
	}: {
		label: string;
		options: { value: string; label: string }[];
		value: string;
		onchange: (value: string) => void;
	} = $props();

	let open = $state(false);
	const active = $derived(options.find((o) => o.value === value));
</script>

<Popover.Root bind:open>
	<Popover.Trigger
		class="cursor-pointer rounded-full border px-2.5 py-1 text-xs tracking-wide {active
			? 'border-amber-soft-border bg-amber-soft-bg text-amber-soft-fg'
			: 'border-border-strong text-muted hover:text-ink hover:border-border-hover'}"
	>
		{active ? active.label : label} ▾
	</Popover.Trigger>
	<Popover.Portal>
		<Popover.Content
			class="border-border bg-panel z-30 flex max-h-64 w-56 flex-col gap-0.5 overflow-y-auto rounded-lg border p-1.5 text-sm"
			sideOffset={6}
		>
			<button
				class="hover:bg-hover cursor-pointer rounded px-2.5 py-1.5 text-left {!value
					? 'text-amber'
					: 'text-ink-3'}"
				onclick={() => {
					onchange('');
					open = false;
				}}
			>
				any
			</button>
			{#each options as opt (opt.value)}
				<button
					class="hover:bg-hover cursor-pointer rounded px-2.5 py-1.5 text-left {value === opt.value
						? 'text-amber'
						: 'text-ink-3'}"
					onclick={() => {
						onchange(opt.value);
						open = false;
					}}
				>
					{opt.label}
				</button>
			{/each}
		</Popover.Content>
	</Popover.Portal>
</Popover.Root>
