<script lang="ts">
	import Modal from './Modal.svelte';

	let {
		open = $bindable(false),
		title = 'Delete this?',
		message,
		confirmLabel = 'delete',
		onConfirm
	}: {
		open?: boolean;
		title?: string;
		message: string;
		confirmLabel?: string;
		onConfirm: () => void | Promise<void>;
	} = $props();

	let busy = $state(false);

	async function confirm() {
		busy = true;
		try {
			await onConfirm();
			open = false;
		} finally {
			busy = false;
		}
	}
</script>

<Modal bind:open {title}>
	{#snippet children()}
		<p class="text-ink-2 text-sm">{message}</p>
	{/snippet}
	{#snippet footer()}
		<button
			class="border-border-strong text-ink-3 hover:border-border-hover hover:text-ink cursor-pointer rounded-lg border px-4 py-2 text-sm"
			onclick={() => (open = false)}
		>
			cancel
		</button>
		<button
			class="text-danger-text hover:border-red border-border-strong cursor-pointer rounded-lg border px-4 py-2 text-sm disabled:opacity-50"
			disabled={busy}
			onclick={confirm}
		>
			{busy ? 'deleting…' : confirmLabel}
		</button>
	{/snippet}
</Modal>
