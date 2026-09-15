<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { apiGet } from '$lib/api';
	import type { BrowseMeta, BrowseResults } from '$lib/types';
	import { headerState } from '$lib/chrome.svelte';
	import ArtPlaceholder from '$lib/components/ArtPlaceholder.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import FacetPopover from '$lib/components/FacetPopover.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import { imageSrc } from '$lib/format';

	const tabs = [
		{ value: 'releases', label: 'releases' },
		{ value: 'artists', label: 'artists' },
		{ value: 'labels', label: 'labels' }
	] as const;

	const sortOptions: Record<string, { value: string; label: string }[]> = {
		releases: [
			{ value: 'listened', label: 'listened' },
			{ value: 'rating', label: 'rating' },
			{ value: 'year', label: 'year' },
			{ value: 'az', label: 'a–z' }
		],
		artists: [
			{ value: 'releases', label: 'releases' },
			{ value: 'rating', label: 'rating' },
			{ value: 'az', label: 'a–z' }
		],
		labels: [
			{ value: 'releases', label: 'releases' },
			{ value: 'rating', label: 'rating' },
			{ value: 'az', label: 'a–z' }
		]
	};

	const entity = $derived(page.params.entity as 'releases' | 'artists' | 'labels');

	let meta = $state<BrowseMeta | null>(null);
	let results = $state<BrowseResults | null>(null);
	let view = $state<'grid' | 'list'>('grid');
	let q = $state('');
	let country = $state('');
	let genre = $state('');
	let type = $state('');
	let ratingMin = $state('');
	let sort = $state('listened');
	let pageNum = $state(1);

	async function loadMeta() {
		meta = await apiGet<BrowseMeta>(`/browse/${entity}`);
	}

	async function loadResults() {
		const params = new URLSearchParams();
		if (q) params.set('q', q);
		if (country) params.set('country', country);
		if (ratingMin) params.set('rating_min', ratingMin);
		if (entity === 'releases' && genre) params.set('genre', genre);
		if (entity !== 'releases' && type) params.set('type', type);
		params.set('sort', sort);
		params.set('page', String(pageNum));
		results = await apiGet<BrowseResults>(`/browse/${entity}/results?${params}`);
	}

	function switchTab(next: string) {
		if (next === entity) return;
		q = '';
		country = '';
		genre = '';
		type = '';
		ratingMin = '';
		sort = next === 'releases' ? 'listened' : 'releases';
		pageNum = 1;
		goto(`/browse/${next}`);
	}

	function goPage(p: number) {
		pageNum = p;
	}

	$effect(() => {
		// re-fetch tab metadata whenever the entity segment changes
		entity;
		loadMeta();
	});

	$effect(() => {
		// re-fetch results whenever any filter/sort/page/entity changes
		entity;
		q;
		country;
		genre;
		type;
		ratingMin;
		sort;
		pageNum;
		loadResults();
	});

	$effect(() => {
		headerState.counter = counterSnippet;
	});

	function clearFilters() {
		q = '';
		country = '';
		genre = '';
		type = '';
		ratingMin = '';
		pageNum = 1;
	}

	const hasActiveFilters = $derived(!!(q || country || genre || type || ratingMin));
</script>

{#snippet counterSnippet()}
	{#if meta}
		<span>{meta.counts[entity].toLocaleString()} {entity}</span>
	{/if}
{/snippet}

<div class="flex flex-col gap-5 p-7">
	<div class="flex flex-wrap items-center gap-4">
		<div class="border-border bg-panel flex gap-1 rounded-lg border p-1">
			{#each tabs as t (t.value)}
				<button
					class="cursor-pointer rounded-md px-3.5 py-1.5 text-sm font-semibold {entity === t.value
						? 'bg-amber text-on-amber'
						: 'text-muted hover:text-ink'}"
					onclick={() => switchTab(t.value)}
				>
					{t.label}
				</button>
			{/each}
		</div>

		<input
			placeholder="search {entity}…"
			bind:value={q}
			oninput={() => (pageNum = 1)}
			class="border-border-strong bg-field focus:border-amber min-w-[180px] flex-1 rounded-lg border px-3 py-2 text-sm outline-none"
		/>

		{#if meta}
			<FacetPopover
				label="country"
				options={meta.filters.countries.map(([code, name]) => ({ value: code, label: name }))}
				value={country}
				onchange={(v) => {
					country = v;
					pageNum = 1;
				}}
			/>
			{#if entity === 'releases' && meta.filters.genres}
				<FacetPopover
					label="genre"
					options={meta.filters.genres.map((g) => ({ value: g, label: g }))}
					value={genre}
					onchange={(v) => {
						genre = v;
						pageNum = 1;
					}}
				/>
			{/if}
			{#if entity !== 'releases' && meta.filters.types}
				<FacetPopover
					label="type"
					options={meta.filters.types.map((t) => ({ value: t, label: t }))}
					value={type}
					onchange={(v) => {
						type = v;
						pageNum = 1;
					}}
				/>
			{/if}
		{/if}

		<select
			bind:value={sort}
			onchange={() => (pageNum = 1)}
			class="border-border-strong bg-field rounded-lg border px-2.5 py-2 text-sm outline-none"
		>
			{#each sortOptions[entity] as opt (opt.value)}
				<option value={opt.value}>sort: {opt.label}</option>
			{/each}
		</select>

		<div class="border-border bg-panel ml-auto flex gap-1 rounded-lg border p-1">
			<button
				class="cursor-pointer rounded-md px-2.5 py-1 text-sm {view === 'grid'
					? 'bg-hover text-ink'
					: 'text-muted'}"
				onclick={() => (view = 'grid')}
			>
				grid
			</button>
			<button
				class="cursor-pointer rounded-md px-2.5 py-1 text-sm {view === 'list'
					? 'bg-hover text-ink'
					: 'text-muted'}"
				onclick={() => (view = 'list')}
			>
				list
			</button>
		</div>
	</div>

	{#if hasActiveFilters}
		<div class="flex flex-wrap items-center gap-2">
			{#if q}
				<Chip label={`"${q}"`} active removable onclick={() => (q = '')} />
			{/if}
			{#if country}
				<Chip
					label={meta?.filters.countries.find(([c]) => c === country)?.[1] ?? country}
					active
					removable
					onclick={() => (country = '')}
				/>
			{/if}
			{#if genre}
				<Chip label={genre} active removable onclick={() => (genre = '')} />
			{/if}
			{#if type}
				<Chip label={type} active removable onclick={() => (type = '')} />
			{/if}
			{#if ratingMin}
				<Chip label={`${ratingMin}+`} active removable onclick={() => (ratingMin = '')} />
			{/if}
			<button class="text-xs text-muted hover:text-ink cursor-pointer" onclick={clearFilters}>
				clear all
			</button>
		</div>
	{/if}

	{#if results}
		{#if results.items.length === 0}
			<p class="text-sm text-muted-2 py-10 text-center">No {entity} match these filters.</p>
		{:else if view === 'grid'}
			<div class="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-4">
				{#each results.items as item (item.id)}
					<a href={item.href} class="flex min-w-0 flex-col gap-2">
						<div class="relative aspect-square overflow-hidden rounded-md">
							<ArtPlaceholder
								artKey={item.art_key}
								hasArt={item.has_art}
								src={imageSrc(item.art_type, item.id)}
								size="100%"
								radius=""
								textClass="text-xs font-bold tracking-wider text-muted-2"
							/>
							<span
								class="bg-hover text-ink absolute bottom-1.5 left-1.5 rounded px-1.5 py-0.5 text-sm font-semibold"
							>
								{item.score.toFixed(1)}
							</span>
						</div>
						<div class="flex min-w-0 flex-col gap-0.5">
							<span class="text-md leading-tight text-pretty">{item.name}</span>
							<span class="text-sm text-muted">{item.meta}</span>
						</div>
					</a>
				{/each}
			</div>
		{:else}
			<div class="flex flex-col gap-1">
				{#each results.items as item (item.id)}
					<a
						href={item.href}
						class="hover:bg-panel grid grid-cols-[40px_minmax(0,1fr)_auto] items-center gap-3.5 rounded-lg px-2 py-2"
					>
						<ArtPlaceholder
							artKey={item.art_key}
							hasArt={item.has_art}
							src={imageSrc(item.art_type, item.id)}
							size="40px"
							radius="rounded-sm"
						/>
						<div class="flex min-w-0 flex-col">
							<span class="text-md">{item.name}</span>
							<span class="text-sm text-muted">{item.meta}</span>
						</div>
						<span class="text-md font-semibold">{item.score.toFixed(1)}</span>
					</a>
				{/each}
			</div>
		{/if}

		{#if results.total_pages > 1}
			<Pagination page={results.page} totalPages={results.total_pages} onchange={goPage} />
		{/if}
	{/if}
</div>
