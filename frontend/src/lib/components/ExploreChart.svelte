<script lang="ts">
	import { resolve } from '$app/paths';
	import type { ExploreResponse, ExploreRow } from '$lib/types';

	let { data }: { data: ExploreResponse } = $props();

	const TIME_DIMS = new Set(['listen_year', 'release_year', 'release_decade', 'listen_month']);
	const MONTH_KEY: Record<string, number> = {
		JAN: 1,
		FEB: 2,
		MAR: 3,
		APR: 4,
		MAY: 5,
		JUN: 6,
		JUL: 7,
		AUG: 8,
		SEP: 9,
		OCT: 10,
		NOV: 11,
		DEC: 12
	};

	const isTime = $derived(TIME_DIMS.has(data.meta.group_by));

	const maxValue = $derived(Math.max(0, ...data.rows.map((r) => r.value)));

	function timeKey(r: ExploreRow): number {
		if (data.meta.group_by === 'listen_month') return MONTH_KEY[r.label] ?? 0;
		const n = parseInt(r.label, 10);
		return Number.isNaN(n) ? 0 : n;
	}

	const sorted = $derived(
		isTime ? [...data.rows].sort((a, b) => timeKey(a) - timeKey(b)) : data.rows
	);

	const width = (v: number) => (maxValue ? Math.round((v / maxValue) * 100) : 0);
	const height = (v: number) => (maxValue ? Math.max(Math.round((v / maxValue) * 100), 2) : 0);
</script>

{#if isTime}
	<div class="flex h-42.5 items-end gap-1.5">
		{#each sorted as row (row.label)}
			<div class="flex h-full flex-1 flex-col items-center justify-end gap-1.5">
				<span class="text-2xs text-muted">{row.display}</span>
				<div
					class="w-full rounded-sm {height(row.value) >= 100 ? 'bg-amber' : 'bg-bar-dim'}"
					style="height:{height(row.value)}%"
				></div>
				<span class="text-2xs text-muted-2">{row.label}</span>
			</div>
		{/each}
	</div>
{:else}
	<div class="flex flex-col gap-2.5">
		{#each sorted as row, i (row.label + i)}
			<div class="grid grid-cols-[18px_minmax(0,1fr)_auto] items-center gap-2.5">
				<span class="text-xs text-muted-2">{i + 1}</span>
				<div class="flex min-w-0 flex-col gap-1">
					<div class="flex items-baseline justify-between gap-2">
						{#if row.href}
							<a
								href={resolve(row.href as `/artist/${string}` | `/label/${string}`)}
								class="text-sm leading-tight hover:underline"
							>
								{row.label}
							</a>
						{:else}
							<span class="text-sm leading-tight">{row.label}</span>
						{/if}
						{#if row.sub}
							<span class="text-2xs whitespace-nowrap text-muted-2">{row.sub}</span>
						{/if}
					</div>
					<div class="h-[3px] overflow-hidden rounded-sm bg-line">
						<div class="h-[3px] rounded-sm bg-amber" style="width:{width(row.value)}%"></div>
					</div>
				</div>
				<span class="min-w-[64px] text-right text-sm text-ink-2">{row.display}</span>
			</div>
		{/each}
	</div>
{/if}
