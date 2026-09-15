<script lang="ts">
	import { Dialog } from 'bits-ui';

	let {
		open = $bindable(false),
		title,
		children,
		footer
	}: {
		open?: boolean;
		title: string;
		children: import('svelte').Snippet;
		footer?: import('svelte').Snippet;
	} = $props();
</script>

<Dialog.Root bind:open>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/60" />
		<Dialog.Content
			class="border-border bg-panel fixed top-1/2 left-1/2 z-50 flex max-h-[85vh] w-[min(480px,92vw)] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 overflow-y-auto rounded-xl border p-6"
		>
			<div class="flex items-center justify-between gap-4">
				<Dialog.Title class="text-lg font-bold tracking-tight">{title}</Dialog.Title>
				<Dialog.Close
					class="text-muted hover:text-ink cursor-pointer text-lg leading-none">×</Dialog.Close
				>
			</div>
			{@render children()}
			{#if footer}
				<div class="border-line flex justify-end gap-2 border-t pt-4">
					{@render footer()}
				</div>
			{/if}
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
