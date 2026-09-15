<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { apiGet } from '$lib/api';
	import type { CompletedGoal, HomeData, HomeEntriesResponse, HomeEntryGroup } from '$lib/types';
	import { headerState } from '$lib/chrome.svelte';
	import { goalNoticeState } from '$lib/goalNotice.svelte';
	import ArtPlaceholder from '$lib/components/ArtPlaceholder.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import { imageSrc } from '$lib/format';

	let home = $state<HomeData | null>(null);
	let groups = $state<HomeEntryGroup[]>([]);
	let page = $state(1);
	let hasNext = $state(false);
	let loadingMore = $state(false);
	let query = $state('');
	let completedGoals = $state<CompletedGoal[]>([]);
	let showGoalModal = $state(false);

	async function loadHome() {
		home = await apiGet<HomeData>('/home');
	}

	async function loadEntries(p: number, append: boolean) {
		const res = await apiGet<HomeEntriesResponse>(`/home/entries?page=${p}`);
		groups = append ? [...groups, ...res.groups] : res.groups;
		hasNext = res.has_next;
		page = res.page;
	}

	onMount(async () => {
		if (goalNoticeState.pending.length) {
			completedGoals = goalNoticeState.pending;
			goalNoticeState.pending = [];
			showGoalModal = true;
		}
		await Promise.all([loadHome(), loadEntries(1, false)]);
	});

	$effect(() => {
		headerState.counter = counterSnippet;
	});

	async function loadEarlier() {
		loadingMore = true;
		try {
			await loadEntries(page + 1, true);
		} finally {
			loadingMore = false;
		}
	}

	function goLog() {
		const q = query.trim();
		goto(q ? `/new?q=${encodeURIComponent(q)}` : '/new');
	}
</script>

{#snippet counterSnippet()}
	{#if home}
		<span>{home.total_logged.toLocaleString()} logged</span>
		<span class="bg-border h-3.5 w-px"></span>
		<span>day {home.day_of_year} / {home.current_year}</span>
	{/if}
{/snippet}

<div class="flex flex-wrap items-start gap-7 p-7">
	<main class="flex min-w-0 flex-1 basis-[540px] flex-col gap-6.5">
		<section
			class="border-border bg-panel flex flex-wrap items-center gap-2.5 rounded-lg border px-4 py-3.5"
		>
			<span class="text-amber text-base">›</span>
			<input
				type="text"
				placeholder="log a release — artist, title, or MBID"
				bind:value={query}
				onkeydown={(e) => e.key === 'Enter' && goLog()}
				class="min-w-[240px] flex-1 bg-transparent text-base outline-none"
			/>
			<div class="flex items-center gap-2">
				<span class="text-xs text-muted tracking-wider">TODAY</span>
				<button
					class="bg-amber text-on-amber hover:bg-amber-hover cursor-pointer rounded-md px-3.5 py-1.5 text-sm font-bold tracking-wide"
					onclick={goLog}
				>
					LOG
				</button>
			</div>
		</section>

		<div class="flex items-baseline justify-between gap-4">
			<h2 class="text-lg font-bold tracking-widest uppercase">Recent listening</h2>
			<span class="text-sm text-muted">sorted by listen date ↓</span>
		</div>

		{#each groups as group (group.label)}
			<section class="mb-1 flex flex-col gap-0.5">
				<div class="flex items-center gap-3.5 px-0.5 pb-2.5">
					<span class="text-amber text-sm font-bold tracking-wider">{group.label}</span>
					<span class="bg-line h-px flex-1"></span>
					<span class="text-sm text-muted">{group.meta}</span>
				</div>

				{#each group.items as item (item.id)}
					<a
						href="/release/{item.id}"
						class="border-border/0 hover:bg-panel hover:border-border grid grid-cols-[68px_minmax(0,1fr)_auto] items-start gap-4.5 rounded-lg border px-3 py-3.5"
					>
						<ArtPlaceholder
							artKey={item.art_key}
							hasArt={item.has_art}
							src={imageSrc('release', item.id)}
						/>

						<div class="flex min-w-0 flex-col gap-1.5">
							<div class="flex flex-wrap items-baseline gap-2">
								<span class="text-lg leading-tight font-medium tracking-tight">{item.title}</span>
								<span class="text-sm text-muted">{item.year ?? ''}</span>
							</div>
							<div class="flex flex-wrap items-center gap-2 text-sm">
								{#if item.artist}
									<span class="text-ink-3">{item.artist.name}</span>
								{/if}
								{#if item.artist && item.label}
									<span class="text-line">/</span>
								{/if}
								{#if item.label}
									<span class="text-ink-3">{item.label.name}</span>
								{/if}
							</div>
							<div class="mt-0.5 flex flex-wrap gap-1.5">
								{#if item.main_genre}
									<span
										class="border-border-strong text-muted-2 rounded-full border px-2 py-0.5 text-2xs tracking-wide"
									>
										{item.main_genre}
									</span>
								{/if}
								{#each item.subgenres as sub (sub)}
									<span class="text-muted rounded-full px-2 py-0.5 text-2xs tracking-wide">{sub}</span
									>
								{/each}
							</div>
							{#if item.note}
								<p class="text-md text-ink-3 mt-1.5 max-w-[58ch] text-pretty italic">
									{item.note}
								</p>
							{/if}
						</div>

						<div class="flex min-w-[96px] flex-col items-end gap-2">
							<div class="flex items-baseline gap-0.5">
								<span class="text-2xl leading-none font-medium tracking-tight">{item.score}</span>
								<span class="text-2xs text-muted">/10</span>
							</div>
							<div class="bg-border h-[3px] w-22 overflow-hidden rounded-sm">
								<div class="bg-amber h-[3px] rounded-sm" style="width:{item.score * 10}%"></div>
							</div>
							<span class="text-xs text-muted-2"
								>{item.runtime} · {item.track_count} tracks</span
							>
						</div>
					</a>
				{/each}
			</section>
		{/each}

		{#if hasNext}
			<button
				class="border-border-strong text-ink-3 hover:border-border-hover hover:text-ink w-fit cursor-pointer rounded-lg border px-4 py-2 text-sm tracking-wide disabled:opacity-50"
				disabled={loadingMore}
				onclick={loadEarlier}
			>
				{loadingMore ? 'LOADING…' : 'LOAD EARLIER ↓'}
			</button>
		{/if}
	</main>

	<aside class="flex min-w-[260px] flex-1 basis-[290px] flex-col gap-4">
		{#if home}
			<section class="border-border bg-panel rounded-xl border p-5">
				<div class="text-xs text-muted tracking-wider">THIS YEAR</div>
				<div class="mt-2.5 flex items-baseline gap-2">
					<span class="text-4xl leading-none font-medium tracking-tighter"
						>{home.this_year.count}</span
					>
					<span class="text-sm text-muted">releases</span>
				</div>
				<div class="mt-4 grid grid-cols-[1fr_auto] gap-x-3 gap-y-1.5 text-sm">
					<span class="text-ink-3">new artists</span><span>{home.this_year.new_artists}</span>
					<span class="text-ink-3">new labels</span><span>{home.this_year.new_labels}</span>
					<span class="text-ink-3">listening time</span><span
						>{home.this_year.listening_time}h</span
					>
					<span class="text-ink-3">average score</span><span
						>{home.this_year.average_score}</span
					>
					<span class="text-ink-3">pace</span>
					<span class="text-amber">{home.this_year.pace} / day</span>
				</div>
			</section>

			{#if home.goal}
				<section class="border-border bg-panel rounded-xl border p-5">
					<div class="flex items-baseline justify-between gap-2.5">
						<span class="text-xs text-muted tracking-wider">GOAL</span>
						<span class="text-xs" class:text-danger-text={!home.goal.on_track}
							>{home.goal.on_track ? 'ON TRACK' : 'BEHIND PACE'}</span
						>
					</div>
					<div class="mt-2.5 text-md">
						{home.goal.amount}
						{home.goal.type}{home.goal.amount === 1 ? '' : 's'} in {home.goal.end_year}
					</div>
					<div class="mt-3 flex items-baseline gap-1.5">
						<span class="text-3xl leading-none font-medium tracking-tight"
							>{Math.round((home.goal.current / home.goal.amount) * 100)}</span
						>
						<span class="text-sm text-muted">% complete</span>
					</div>
					<div class="bg-border mt-3 h-1.5 overflow-hidden rounded-sm">
						<div
							class="bg-cyan h-1.5 rounded-sm"
							style="width:{Math.min(
								Math.round((home.goal.current / home.goal.amount) * 100),
								100
							)}%"
						></div>
					</div>
					<div class="mt-3.5 grid grid-cols-[1fr_auto] gap-x-3 gap-y-1.5 text-sm">
						<span class="text-ink-3">remaining</span><span
							>{Math.max(home.goal.amount - home.goal.current, 0)}</span
						>
					</div>
				</section>
			{/if}

			<section class="border-border bg-panel rounded-xl border p-5">
				<div class="text-xs text-muted tracking-wider">SCORE SPREAD</div>
				<div class="mt-4 flex h-16 items-end gap-1.5">
					{#each home.score_spread as bucket, i (i)}
						<div
							class="flex-1 rounded-sm {bucket.is_peak ? 'bg-amber' : 'bg-bar-dim'}"
							style="height:{Math.max(bucket.pct, 3)}%"
						></div>
					{/each}
				</div>
				<div class="mt-2 flex justify-between text-2xs text-muted-2">
					<span>1</span><span>median {home.median_score}</span><span>10</span>
				</div>
			</section>

			<section class="border-border bg-panel rounded-xl border p-5">
				<div class="text-xs text-muted tracking-wider">ON REPEAT — 90 DAYS</div>
				<div class="mt-3.5 flex flex-col gap-3">
					{#each home.on_repeat as entity (entity.id)}
						<a href="/artist/{entity.id}" class="flex items-center gap-3">
							<ArtPlaceholder
								artKey={entity.art_key}
								hasArt={entity.has_art}
								src={imageSrc('artist', entity.id)}
								size="34px"
								radius="rounded-sm"
							/>
							<div class="min-w-0 flex-1">
								<span class="text-md">{entity.name}</span>
								<div class="text-xs text-muted-2">
									{entity.count} release{entity.count === 1 ? '' : 's'} · avg {entity.average_rating.toFixed(
										1
									)}
								</div>
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}
	</aside>
</div>

<Modal bind:open={showGoalModal} title="🎉 Goal complete!">
	<div class="flex flex-col gap-2">
		{#each completedGoals as goal (goal.type + goal.end_year)}
			<p class="text-md">
				You hit your goal of {goal.amount}
				{goal.type}{goal.amount === 1 ? '' : 's'} in {goal.end_year}.
			</p>
		{/each}
	</div>
</Modal>
