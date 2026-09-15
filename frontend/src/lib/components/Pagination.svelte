<script lang="ts">
	let {
		page,
		totalPages,
		onchange
	}: { page: number; totalPages: number; onchange: (page: number) => void } = $props();
</script>

<div class="flex items-center justify-center gap-4">
	<button
		class="border-border-strong text-muted hover:border-border-hover hover:text-ink cursor-pointer rounded-lg border px-4 py-2 text-sm tracking-wide disabled:cursor-default disabled:opacity-40"
		disabled={page <= 1}
		onclick={() => onchange(page - 1)}
	>
		← back
	</button>
	<span class="text-sm text-muted">page {page} of {totalPages}</span>
	<button
		class="border-border-strong text-muted hover:border-border-hover hover:text-ink cursor-pointer rounded-lg border px-4 py-2 text-sm tracking-wide disabled:cursor-default disabled:opacity-40"
		disabled={page >= totalPages}
		onclick={() => onchange(page + 1)}
	>
		next →
	</button>
</div>
