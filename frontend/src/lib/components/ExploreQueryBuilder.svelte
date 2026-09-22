<script lang="ts">
	import FacetPopover from './FacetPopover.svelte';
	import type { ExploreFieldDef, ExploreFilterState, ExploreOptions } from '$lib/types';

	let {
		options,
		rows = $bindable([]),
		groupBy = $bindable('artist'),
		metric = $bindable('count'),
		minItems = $bindable(1),
		order = $bindable<'desc' | 'asc'>('desc'),
		limit = $bindable(15)
	}: {
		options: ExploreOptions;
		rows: ExploreFilterState[];
		groupBy: string;
		metric: string;
		minItems: number;
		order: 'desc' | 'asc';
		limit: number;
	} = $props();

	const fieldByValue = $derived(
		Object.fromEntries(options.fields.map((f) => [f.value, f])) as Record<string, ExploreFieldDef>
	);

	const addOptions = $derived(options.fields.map((f) => ({ value: f.value, label: f.label })));

	const optionPairs = $derived.by(() => {
		const acc: Record<string, { value: string; label: string }[]> = {};
		for (const def of options.fields) {
			if (def.kind !== 'enum' || !def.options) continue;
			const list = options.options[def.options as keyof ExploreOptions['options']];
			acc[def.options] =
				Array.isArray(list) && list.length > 0 && Array.isArray(list[0])
					? (list as [string, string][]).map(([value, label]) => ({ value, label }))
					: (list as string[]).map((value) => ({ value, label: value }));
		}
		return acc;
	});

	function addRow(field: string) {
		const def = fieldByValue[field];
		if (!def) return;
		rows.push({ field, kind: def.kind });
	}

	function removeRow(index: number) {
		rows.splice(index, 1);
	}

	function boundsFor(row: ExploreFilterState): [number, number] | undefined {
		return options.bounds[row.field];
	}
</script>

<section class="flex flex-col gap-4 rounded-xl border border-border bg-panel p-5">
	<div class="flex flex-wrap items-center gap-2">
		{#each rows as row, i (row.field + i)}
			<div
				class="flex items-center gap-2 rounded-lg border border-border-strong bg-field px-2 py-1.5"
			>
				<span class="text-sm font-semibold whitespace-nowrap">
					{fieldByValue[row.field]?.label ?? row.field}
				</span>

				{#if row.kind === 'text'}
					<input
						type="text"
						placeholder="contains…"
						bind:value={row.text}
						class="w-36 rounded-md border border-border-strong bg-transparent px-2 py-1 text-sm outline-none placeholder:text-muted-2 focus:border-amber"
					/>
				{:else if row.kind === 'enum'}
					<FacetPopover
						label="any"
						options={optionPairs[fieldByValue[row.field]?.options ?? ''] ?? []}
						value={row.enumValue ?? ''}
						onchange={(v) => (row.enumValue = v)}
					/>
				{:else if row.kind === 'years'}
					<div class="flex items-center gap-1">
						<input
							type="number"
							placeholder="from"
							min={1000}
							max={2100}
							bind:value={row.lo}
							class="w-20 rounded-md border border-border-strong bg-transparent px-2 py-1 text-sm outline-none placeholder:text-muted-2 focus:border-amber"
						/>
						<span class="text-xs text-muted-2">→</span>
						<input
							type="number"
							placeholder="to"
							min={1000}
							max={2100}
							bind:value={row.hi}
							class="w-20 rounded-md border border-border-strong bg-transparent px-2 py-1 text-sm outline-none placeholder:text-muted-2 focus:border-amber"
						/>
					</div>
				{:else if row.kind === 'range'}
					{@const bounds = boundsFor(row)}
					<div class="flex items-center gap-1">
						<input
							type="number"
							placeholder={String(bounds?.[0] ?? '')}
							bind:value={row.lo}
							class="w-20 rounded-md border border-border-strong bg-transparent px-2 py-1 text-sm outline-none placeholder:text-muted-2 focus:border-amber"
						/>
						<span class="text-xs text-muted-2">–</span>
						<input
							type="number"
							placeholder={String(bounds?.[1] ?? '')}
							bind:value={row.hi}
							class="w-20 rounded-md border border-border-strong bg-transparent px-2 py-1 text-sm outline-none placeholder:text-muted-2 focus:border-amber"
						/>
					</div>
				{/if}

				<button
					class="cursor-pointer rounded px-1 text-sm text-muted-2 hover:text-red"
					aria-label="remove filter"
					onclick={() => removeRow(i)}
				>
					✕
				</button>
			</div>
		{/each}

		<FacetPopover label="add filter" options={addOptions} value="" onchange={addRow} />
	</div>

	<div class="flex flex-wrap items-center gap-x-5 gap-y-2.5 border-t border-line pt-3.5 text-sm">
		<label class="flex items-center gap-2">
			<span class="text-muted">group by</span>
			<select
				bind:value={groupBy}
				class="rounded-md border border-border-strong bg-field px-2 py-1.5 text-sm outline-none"
			>
				{#each options.group_bys as g (g.value)}
					<option value={g.value}>{g.label}</option>
				{/each}
			</select>
		</label>

		<label class="flex items-center gap-2">
			<span class="text-muted">metric</span>
			<select
				bind:value={metric}
				class="rounded-md border border-border-strong bg-field px-2 py-1.5 text-sm outline-none"
			>
				{#each options.metrics as m (m.value)}
					<option value={m.value}>{m.label}</option>
				{/each}
			</select>
		</label>

		<div class="flex items-center gap-1 rounded-md border border-border p-0.5">
			<button
				class="cursor-pointer rounded px-2 py-1 text-sm {order === 'desc'
					? 'bg-hover text-ink'
					: 'text-muted'}"
				onclick={() => (order = 'desc')}
			>
				top
			</button>
			<button
				class="cursor-pointer rounded px-2 py-1 text-sm {order === 'asc'
					? 'bg-hover text-ink'
					: 'text-muted'}"
				onclick={() => (order = 'asc')}
			>
				bottom
			</button>
		</div>

		<label class="flex items-center gap-2">
			<span class="text-muted">min releases</span>
			<input
				type="number"
				min={1}
				bind:value={minItems}
				class="w-16 rounded-md border border-border-strong bg-field px-2 py-1.5 text-sm outline-none"
			/>
		</label>

		<label class="flex items-center gap-2">
			<span class="text-muted">show</span>
			<select
				bind:value={limit}
				class="rounded-md border border-border-strong bg-field px-2 py-1.5 text-sm outline-none"
			>
				{#each [5, 10, 15, 25, 50] as n (n)}
					<option value={n}>{n}</option>
				{/each}
			</select>
		</label>
	</div>
</section>
