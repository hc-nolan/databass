<script lang="ts">
	import { onMount } from 'svelte';
	import { apiGet, apiPost } from '$lib/api';
	import { headerState } from '$lib/chrome.svelte';
	import StatsTabs from '$lib/components/StatsTabs.svelte';
	import type { ListenBrainzStats } from '$lib/types';

	let range = $state('all_time');
	let data = $state<ListenBrainzStats | null>(null);
	let loading = $state(false);
	let syncing = $state(false);
	const ranges = [['this_week', 'week'], ['this_month', 'month'], ['this_year', 'year'], ['all_time', 'all time']];

	async function load() {
		loading = true;
		try { data = await apiGet<ListenBrainzStats>(`/listenbrainz/stats?range=${range}`); }
		finally { loading = false; }
	}

	async function syncNow() {
		syncing = true;
		try {
			await apiPost('/listenbrainz/sync');
			await load();
		} finally { syncing = false; }
	}
	onMount(load);
	$effect(() => { headerState.counter = counterSnippet; });
	const artists = $derived(data?.artists?.artists ?? []);
	const releases = $derived(data?.releases?.releases ?? []);
	const recordings = $derived(data?.recordings?.recordings ?? []);
	const activity = $derived(data?.listening_activity?.listening_activity ?? []);
	const maxActivity = $derived(Math.max(...activity.map((x) => x.listen_count), 1));
	const daily = $derived(data?.daily_activity?.daily_activity ?? {});
	const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
	const dailyColumns = $derived(weekdays.map((day) => ({
		day,
		hours: daily[day] ?? []
	})));
	const maxDaily = $derived(Math.max(...Object.values(daily).flatMap((hours) => hours.map((x) => x.listen_count)), 1));
	const countryMap = $derived(data?.artist_map?.artist_map ?? []);
	const maxCountry = $derived(Math.max(...countryMap.map((x) => x.artist_count), 1));
</script>

{#snippet counterSnippet()}
	{#if data?.listen_count != null}<span>{data.listen_count.toLocaleString()} listens</span>{/if}
{/snippet}

<div class="mx-auto flex max-w-[1440px] flex-col gap-5 p-7">
	<div class="flex flex-wrap items-center gap-4"><StatsTabs /><h1 class="text-lg font-bold tracking-widest uppercase">ListenBrainz stats</h1>
		<div class="flex gap-1 rounded-lg border border-border bg-panel p-1">{#each ranges as r}
			<button class="rounded-md px-3 py-1.5 text-sm font-semibold {range === r[0] ? 'bg-amber text-on-amber' : 'text-muted'}" onclick={() => { range = r[0]; load(); }}>{r[1]}</button>
		{/each}</div>
		<button
			class="cursor-pointer rounded-lg border border-border-strong px-3.5 py-1.5 text-sm text-muted hover:text-ink disabled:opacity-50"
			disabled={syncing}
			onclick={syncNow}
		>
			{syncing ? 'SYNCING…' : 'SYNC NOW'}
		</button>
		{#if data?.configured && data.listen_count != null}
			<span class="text-xs text-muted-2">
				imported {data.imported?.toLocaleString() ?? 0} of {data.listen_count.toLocaleString()}
			</span>
		{/if}
	</div>
	{#if loading}<p class="text-sm text-muted">Loading ListenBrainz…</p>
	{:else if data && !data.configured}<section class="rounded-xl border border-border bg-panel p-5 text-sm text-muted">Set LISTENBRAINZ_USERNAME to enable these stats.</section>
	{:else if data}
		<section class="grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-px overflow-hidden rounded-xl border border-border bg-border">
			{#each [{ label: 'LISTENS', value: data.listen_count ?? 0 }, { label: 'ARTISTS', value: data.artists?.total_artist_count ?? artists.length }, { label: 'TOP ARTIST', value: artists[0]?.artist_name ?? '—' }] as k}
				<div class="flex flex-col gap-1 bg-panel px-4 py-4.5"><span class="text-2xs tracking-wider text-muted">{k.label}</span><span class="text-xl font-medium">{k.value}</span>{#if k.label === 'TOP ARTIST'}<span class="text-xs text-muted">{artists[0]?.listen_count ?? 0} listens</span>{/if}</div>
			{/each}
		</section>
		<div class="grid gap-5 lg:grid-cols-2">
			{#each [{ title: 'TOP ARTISTS', rows: artists.map((x) => ({ name: x.artist_name, count: x.listen_count })) }, { title: 'TOP RELEASES', rows: releases.map((x) => ({ name: `${x.artist_name} — ${x.release_name}`, count: x.listen_count })) }, { title: 'TOP RECORDINGS', rows: recordings.map((x) => ({ name: `${x.artist_name} — ${x.track_name}`, count: x.listen_count })) }] as board}
				<section class="rounded-xl border border-border bg-panel p-5"><span class="text-xs font-bold tracking-widest text-amber">{board.title}</span><div class="mt-4 flex flex-col gap-3">{#each board.rows.slice(0, 10) as row, i}<div class="grid grid-cols-[20px_minmax(0,1fr)_auto] gap-2 text-sm"><span class="text-muted-2">{i + 1}</span><span class="truncate">{row.name}</span><span class="text-muted">{row.count}</span></div>{/each}</div></section>
			{/each}
			<section class="min-w-0 overflow-hidden rounded-xl border border-border bg-panel p-5"><span class="text-xs font-bold tracking-widest text-amber">LISTENING ACTIVITY</span><div class="mt-5 flex h-44 min-w-0 items-end gap-1 overflow-hidden">{#each activity as item}<div class="flex min-w-0 h-full flex-1 flex-col items-center justify-end gap-1"><span class="text-2xs text-muted">{item.listen_count}</span><div class="w-full rounded-sm bg-amber" style={`height:${item.listen_count / maxActivity * 100}%`}></div><span class="w-full truncate text-center text-2xs text-muted-2">{item.time_range}</span></div>{/each}</div></section>
			<section class="min-w-0 overflow-hidden rounded-xl border border-border bg-panel p-5"><span class="text-xs font-bold tracking-widest text-amber">WHEN YOU LISTEN</span><div class="mt-4 grid grid-cols-7 gap-1">{#each dailyColumns as column}<div class="flex min-w-0 flex-col gap-1"><span class="truncate text-2xs text-muted">{column.day.slice(0, 3)}</span>{#each Array.from({ length: 24 }, (_, hour) => column.hours.find((x) => x.hour === hour)?.listen_count ?? 0) as count}<div class="h-2 rounded-sm bg-field" title={`${count} listens`} style={count ? `background-color: color-mix(in srgb, var(--color-amber) ${Math.max(15, count / maxDaily * 100)}%, var(--color-field))` : undefined}></div>{/each}</div>{/each}</div></section>
			<section class="rounded-xl border border-border bg-panel p-5"><span class="text-xs font-bold tracking-widest text-amber">ARTISTS BY COUNTRY</span><div class="mt-4 flex flex-col gap-2.5">{#each countryMap.slice(0, 12) as country}<div class="grid grid-cols-[48px_minmax(0,1fr)_auto] items-center gap-2 text-sm"><span class="text-muted">{country.country}</span><div class="h-1 overflow-hidden rounded bg-line"><div class="h-full rounded bg-cyan" style={`width:${country.artist_count / maxCountry * 100}%`}></div></div><span class="text-muted">{country.artist_count}</span></div>{/each}</div></section>
		</div>
	{/if}
</div>
