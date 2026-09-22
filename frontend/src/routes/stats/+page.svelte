<script lang="ts">
	import { onMount } from 'svelte';
	import { apiGet } from '$lib/api';
	import type { StatsData, StatsPeriod, LeaderboardBoard } from '$lib/types';
	import { headerState } from '$lib/chrome.svelte';
	import StatsTabs from '$lib/components/StatsTabs.svelte';

	let data = $state<StatsData | null>(null);
	let stats = $state<StatsPeriod | null>(null);
	let activePeriod = $state('all');
	let scope = $state<'artists' | 'labels'>('artists');
	let boards = $state<LeaderboardBoard[]>([]);

	async function loadAll() {
		data = await apiGet<StatsData>('/stats');
		stats = data.stats;
		activePeriod = data.active_period;
	}

	async function loadPeriod(key: string) {
		activePeriod = key;
		const res = await apiGet<{ stats: StatsPeriod }>(`/stats/period/${key}`);
		stats = res.stats;
	}

	async function loadBoards(next: 'artists' | 'labels') {
		scope = next;
		const res = await apiGet<{ boards: LeaderboardBoard[] }>(`/stats/leaderboards/${next}`);
		boards = res.boards;
	}

	onMount(async () => {
		await Promise.all([loadAll(), loadBoards('artists')]);
	});

	$effect(() => {
		headerState.counter = counterSnippet;
	});
</script>

{#snippet counterSnippet()}
	{#if data?.since}
		<span>since {data.since}</span>
	{/if}
{/snippet}

<div class="mx-auto flex max-w-[1440px] flex-col gap-5 p-7">
	<div class="flex flex-wrap items-center gap-4">
		<StatsTabs />
		<h1 class="text-lg font-bold tracking-widest uppercase">Listening habits</h1>
		<div class="border-border bg-panel flex gap-1 rounded-lg border p-1">
			{#if data}
				{#each data.periods as p (p.key)}
					<button
						class="cursor-pointer rounded-md px-3.5 py-1.5 text-sm font-semibold {activePeriod ===
						p.key
							? 'bg-amber text-on-amber'
							: 'text-muted hover:text-ink'}"
						onclick={() => loadPeriod(p.key)}
					>
						{p.label}
					</button>
				{/each}
			{/if}
		</div>
	</div>

	{#if stats}
		<section class="border-border bg-panel grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-px overflow-hidden rounded-xl border bg-border">
			{#each stats.kpis as k (k.label)}
				<div class="bg-panel flex flex-col gap-1.5 px-4 py-4.5">
					<span class="text-2xs text-muted tracking-wider">{k.label}</span>
					<span class="text-[26px] leading-tight font-medium tracking-tight">{k.value}</span>
					<span class="text-xs text-muted">{k.sub}</span>
				</div>
			{/each}
		</section>

		<div class="flex flex-wrap gap-5">
			<section class="border-border bg-panel flex min-w-0 flex-2 basis-[520px] flex-col gap-4 rounded-xl border p-5">
				<div class="flex flex-wrap items-baseline justify-between gap-2.5">
					<span class="text-amber text-xs font-bold tracking-widest">WHEN YOU LISTEN</span>
					<span class="text-sm text-muted">{stats.chart_note}</span>
				</div>
				<div class="flex h-42.5 items-end gap-1.5">
					{#each stats.series as b (b.label)}
						<div class="flex h-full flex-1 flex-col items-center justify-end gap-1.5">
							<span class="text-2xs text-muted">{b.value}</span>
							<div
								class="w-full rounded-sm {b.is_peak ? 'bg-amber' : 'bg-bar-dim'}"
								style="height:{b.h}%"
							></div>
							<span class="text-2xs text-muted-2">{b.label}</span>
						</div>
					{/each}
				</div>
				<div class="border-line flex flex-wrap gap-x-5.5 gap-y-2.5 border-t pt-1.5">
					{#each stats.rhythm as r (r.label)}
						<div class="flex flex-col gap-0.5">
							<span class="text-2xs text-muted tracking-wider">{r.label}</span>
							<span class="text-md font-semibold">{r.value}</span>
						</div>
					{/each}
				</div>
			</section>

			<section class="border-border bg-panel flex min-w-[280px] flex-1 basis-[300px] flex-col gap-3.5 rounded-xl border p-5">
				<span class="text-amber text-xs font-bold tracking-widest">HOW YOU RATE</span>
				<div class="flex h-24 items-end gap-1.5">
					{#each stats.histogram as h, i (i)}
						<div class="flex-1 rounded-sm {h.is_peak ? 'bg-amber' : 'bg-bar-dim'}" style="height:{h.h}%"></div>
					{/each}
				</div>
				<div class="flex justify-between text-2xs text-muted-2">
					<span>1</span><span>5</span><span>10</span>
				</div>
				<div class="border-line grid grid-cols-[1fr_auto] gap-x-3 gap-y-2 border-t pt-1.5 text-sm">
					<span class="text-ink-3">mean</span><span>{stats.mean}</span>
					<span class="text-ink-3">median</span><span>{stats.median}</span>
					<span class="text-ink-3">rated 8+</span><span>{stats.high_share}</span>
					<span class="text-ink-3">rated 3-</span><span>{stats.low_share}</span>
				</div>
			</section>
		</div>

		<section class="border-border bg-panel flex flex-col gap-4 rounded-xl border p-5">
			<div class="flex flex-wrap items-center gap-3.5">
				<span class="text-amber text-xs font-bold tracking-widest">LEADERBOARDS</span>
				<div class="border-border-strong flex gap-1 rounded-lg border p-1">
					{#each ['artists', 'labels'] as const as s (s)}
						<button
							class="cursor-pointer rounded-md px-3.5 py-1.5 text-sm font-semibold {scope === s
								? 'bg-hover text-ink'
								: 'text-muted'}"
							onclick={() => loadBoards(s)}
						>
							{s}
						</button>
					{/each}
				</div>
			</div>

			<div class="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-5">
				{#each boards as board (board.title)}
					<div class="flex flex-col gap-3">
						<div class="flex flex-col gap-0.5">
							<span class="text-md font-bold">{board.title}</span>
							<span class="text-sm text-muted text-pretty">{board.note}</span>
						</div>
						{#if board.rows.length === 0}
							<p class="text-sm text-muted-2">Not enough data yet.</p>
						{:else}
							<div class="flex flex-col gap-2.5">
								{#each board.rows as row (row.rank)}
									<div class="grid grid-cols-[18px_minmax(0,1fr)_auto] items-center gap-2.5">
										<span class="text-xs text-muted-2">{row.rank}</span>
										<div class="flex min-w-0 flex-col gap-1">
											<span class="text-sm leading-tight">{row.name}</span>
											<div class="bg-line h-[3px] overflow-hidden rounded-sm">
												<div
													class="h-[3px] rounded-sm {board.title === 'Most frequent'
														? 'bg-cyan'
														: 'bg-amber'}"
													style="width:{row.w}%"
												></div>
											</div>
										</div>
										<span class="text-ink-2 min-w-[54px] text-right text-sm">{row.value}</span>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>

		<section class="border-border bg-panel flex flex-col gap-3.5 rounded-xl border p-5">
			<span class="text-amber text-xs font-bold tracking-widest">WHAT YOU LISTEN TO</span>
			{#if data && data.genres.length === 0}
				<p class="text-sm text-muted-2">Not enough data yet.</p>
			{:else if data}
				<div class="flex flex-col gap-2.5">
					{#each data.genres as g (g.name)}
						<div class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
							<div class="flex min-w-0 flex-col gap-1">
								<span class="text-sm">{g.name}</span>
								<div class="bg-line h-1 overflow-hidden rounded-sm">
									<div
										class="h-1 rounded-sm {g.name === data.genres[0]?.name ? 'bg-amber' : 'bg-bar-dim'}"
										style="width:{g.w}%"
									></div>
								</div>
							</div>
							<span class="text-ink-3 min-w-[76px] text-right text-sm">{g.value}</span>
						</div>
					{/each}
				</div>
			{/if}
		</section>
	{/if}
</div>
