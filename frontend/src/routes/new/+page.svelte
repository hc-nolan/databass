<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page as pageState } from '$app/state';
	import { apiGet, apiPost } from '$lib/api';
	import type {
		ArtCandidate,
		ArtSearchResponse,
		NewListenData,
		SearchResultItem,
		SubmitResponse
	} from '$lib/types';
	import { headerState } from '$lib/chrome.svelte';
	import { goalNoticeState } from '$lib/goalNotice.svelte';
	import { ratingHint } from '$lib/format';
	import ArtPlaceholder from '$lib/components/ArtPlaceholder.svelte';

	let data = $state<NewListenData | null>(null);
	let qRelease = $state(pageState.url.searchParams.get('q') ?? '');
	let qArtist = $state(pageState.url.searchParams.get('artist') ?? '');
	let qLabel = $state('');
	let results = $state<SearchResultItem[]>([]);
	let searched = $state(false);
	let searching = $state(false);
	let selectedIndex = $state<number | null>(null);
	let artCandidates = $state<ArtCandidate[]>([]);
	let artLoading = $state(false);
	let artSearched = $state(false);
	let chosenArt = $state<ArtCandidate | null>(null);
	let artRequest: Promise<void> | null = null;

	let manualMode = $state(false);
	let manual = $state({
		name: '',
		artist: '',
		label: '',
		year: '',
		country: '',
		track_count: '',
		runtime: ''
	});

	let rating = $state(7);
	let listenDate = $state('');
	let genres = $state<string[]>([]);
	let newGenre = $state('');
	let note = $state('');
	let saved = $state(false);
	let saving = $state(false);

	const selected = $derived(selectedIndex != null ? results[selectedIndex] : null);
	const hasSelection = $derived(manualMode ? manual.name.trim().length > 0 : selected != null);

	const artGroups = $derived.by(() => {
		const labels: Record<string, string> = {
			caa: 'COVER ART ARCHIVE',
			discogs: 'DISCOGS'
		};
		return ['caa', 'discogs']
			.map((source) => ({
				source,
				label: labels[source] ?? source.toUpperCase(),
				items: artCandidates.filter((c) => c.source === source)
			}))
			.filter((group) => group.items.length > 0);
	});

	onMount(async () => {
		data = await apiGet<NewListenData>('/new');
		listenDate = data.today;
		if (qRelease || qArtist) doSearch();
	});

	$effect(() => {
		headerState.counter = counterSnippet;
	});

	async function doSearch() {
		if (!qRelease.trim() && !qArtist.trim() && !qLabel.trim()) return;
		searching = true;
		try {
			const res = await apiPost<{ results: SearchResultItem[] }>('/search', {
				release: qRelease.trim() || null,
				artist: qArtist.trim() || null,
				label: qLabel.trim() || null
			});
			results = res.results;
			searched = true;
			selectedIndex = null;
			saved = false;
			artCandidates = [];
			artLoading = false;
			artSearched = false;
			chosenArt = null;
		} finally {
			searching = false;
		}
	}

	function selectResult(i: number) {
		selectedIndex = i;
		saved = false;
		loadArt();
	}

	async function loadArt() {
		const r = selected;
		if (!r) return;
		artLoading = true;
		artSearched = false;
		artCandidates = [];
		chosenArt = null;
		// Track the in-flight request so save() can wait for the picker to
		// finish and a fast save doesn't silently discard the user's art
		// choice (or the auto-pick).
		artRequest = (async () => {
			try {
				const res = await apiPost<ArtSearchResponse>('/art', {
					release_group_mbid: r.release_group_id ?? null,
					release_mbid: r.release.mbid ?? null,
					name: r.release.name,
					artist: r.artist.name
				});
				if (selected !== r) return; // user moved on while we were fetching
				artCandidates = res.candidates;
				chosenArt = res.candidates[0] ?? null;
			} catch {
				if (selected !== r) return;
				artCandidates = [];
			} finally {
				if (selected === r) {
					artLoading = false;
					artSearched = true;
				}
			}
		})();
		await artRequest;
	}

	function artLabel(c: ArtCandidate) {
		return c.label ? `${c.label} art from ${c.source}` : `art from ${c.source}`;
	}

	function toggleGenre(name: string) {
		genres = genres.includes(name) ? genres.filter((g) => g !== name) : [...genres, name];
	}

	function addGenre() {
		const name = newGenre.trim();
		if (name && !genres.includes(name)) genres = [...genres, name];
		newGenre = '';
	}

	function clearForm() {
		rating = 7;
		genres = [];
		note = '';
		saved = false;
	}

	async function save() {
		saving = true;
		try {
			// If the art picker is still loading, wait for it before posting so a
			// fast save doesn't discard the chosen art.
			if (!manualMode) await artRequest;
			let res: SubmitResponse | undefined;
			if (manualMode) {
				res = await apiPost<SubmitResponse>('/submit', {
					manual_submit: true,
					name: manual.name,
					artist: manual.artist,
					label: manual.label,
					year: manual.year || null,
					country: manual.country || null,
					track_count: manual.track_count || 0,
					runtime: manual.runtime || 0,
					main_genre: genres[0] ?? null,
					genres,
					rating: rating * 10,
					listen_date: listenDate,
					note: note || null
				});
			} else if (selected) {
				res = await apiPost<SubmitResponse>('/submit', {
					release_group_id: selected.release_group_id,
					release_name: selected.release.name,
					release_mbid: selected.release.mbid,
					artist: selected.artist.name,
					artist_mbid: selected.artist.mbid,
					label: selected.label.name,
					label_mbid: selected.label.mbid,
					year: selected.date ? new Date(selected.date).getFullYear() : null,
					main_genre: genres[0] ?? null,
					genres,
					rating: rating * 10,
					track_count: selected.track_count,
					listen_date: listenDate,
					country: selected.country,
					image: chosenArt?.url ?? null,
					note: note || null
				});
			}
			saved = true;
			goalNoticeState.pending = res?.completed_goals ?? [];
			goto('/');
		} finally {
			saving = false;
		}
	}
</script>

{#snippet counterSnippet()}
	{#if data}
		<span>{data.total_logged.toLocaleString()} logged</span>
	{/if}
{/snippet}

<div class="flex flex-wrap items-start gap-7 p-7">
	<main class="flex min-w-0 flex-1 basis-[560px] flex-col gap-5">
		<section class="border-border bg-panel flex flex-col gap-3 rounded-xl border p-4.5">
			<div class="flex items-baseline justify-between gap-3">
				<span class="text-amber text-sm font-bold tracking-widest">SEARCH MUSICBRAINZ</span>
				<button
					class="border-border-strong text-muted hover:border-border-hover hover:text-ink cursor-pointer rounded-md border px-2.5 py-1 text-xs"
					onclick={() => (manualMode = !manualMode)}
				>
					{manualMode ? 'search instead' : 'manual entry'}
				</button>
			</div>

			{#if manualMode}
				<div class="grid grid-cols-2 gap-2.5">
					<input
						placeholder="release name"
						bind:value={manual.name}
						class="border-border-strong bg-field focus:border-amber col-span-2 rounded-lg border px-3 py-2 text-base outline-none"
					/>
					<input
						placeholder="artist"
						bind:value={manual.artist}
						class="border-border-strong bg-field focus:border-amber rounded-lg border px-3 py-2 text-base outline-none"
					/>
					<input
						placeholder="label"
						bind:value={manual.label}
						class="border-border-strong bg-field focus:border-amber rounded-lg border px-3 py-2 text-base outline-none"
					/>
					<input
						placeholder="year"
						bind:value={manual.year}
						class="border-border-strong bg-field focus:border-amber rounded-lg border px-3 py-2 text-base outline-none"
					/>
					<input
						placeholder="country"
						bind:value={manual.country}
						class="border-border-strong bg-field focus:border-amber rounded-lg border px-3 py-2 text-base outline-none"
					/>
					<input
						placeholder="track count"
						bind:value={manual.track_count}
						class="border-border-strong bg-field focus:border-amber rounded-lg border px-3 py-2 text-base outline-none"
					/>
					<input
						placeholder="runtime (minutes)"
						bind:value={manual.runtime}
						class="border-border-strong bg-field focus:border-amber rounded-lg border px-3 py-2 text-base outline-none"
					/>
				</div>
			{:else}
				<div class="flex flex-wrap gap-2.5">
					<input
						placeholder="release"
						bind:value={qRelease}
						onkeydown={(e) => e.key === 'Enter' && doSearch()}
						class="border-border-strong bg-field focus:border-amber min-w-[200px] flex-[2_1_200px] rounded-lg border px-3 py-2.5 text-base outline-none"
					/>
					<input
						placeholder="artist"
						bind:value={qArtist}
						onkeydown={(e) => e.key === 'Enter' && doSearch()}
						class="border-border-strong bg-field focus:border-amber min-w-[150px] flex-1 rounded-lg border px-3 py-2.5 text-base outline-none"
					/>
					<input
						placeholder="label"
						bind:value={qLabel}
						onkeydown={(e) => e.key === 'Enter' && doSearch()}
						class="border-border-strong bg-field focus:border-amber min-w-[150px] flex-1 rounded-lg border px-3 py-2.5 text-base outline-none"
					/>
					<button
						class="bg-amber text-on-amber hover:bg-amber-hover cursor-pointer rounded-lg px-5 py-2.5 text-sm font-bold tracking-wide disabled:opacity-50"
						disabled={searching}
						onclick={doSearch}
					>
						{searching ? 'SEARCHING…' : 'SEARCH'}
					</button>
				</div>
				{#if searched}
					<div class="flex flex-wrap items-center gap-2 text-xs text-muted-2">
						<span>{results.length} results for "{qRelease || qArtist || qLabel}"</span>
						<span class="text-line">·</span>
						<span>duplicates of releases you already logged are marked</span>
					</div>
				{/if}
			{/if}
		</section>

		{#if !manualMode}
			<div class="flex flex-col gap-1.5">
				{#each results as r, i (i)}
					<button
						onclick={() => selectResult(i)}
						class="grid cursor-pointer grid-cols-[52px_minmax(0,1fr)_auto] items-center gap-4 rounded-lg border p-3 text-left {selectedIndex ===
						i
							? 'bg-hover border-amber'
							: 'bg-panel-alt border-line hover:border-border-hover'}"
					>
						<div
							class="cover flex h-13 w-13 shrink-0 items-center justify-center rounded-xs"
						>
							<span class="text-2xs text-muted-2 font-bold tracking-wider">{r.initials}</span>
						</div>
						<div class="flex min-w-0 flex-col gap-1">
							<div class="flex flex-wrap items-baseline gap-2">
								<span class="text-md font-medium">{r.release.name}</span>
								{#if r.logged}
									<span
										class="bg-cyan-soft-bg text-cyan-soft-fg rounded-full px-1.5 py-px text-[9.5px] font-bold tracking-wider"
									>
										ALREADY LOGGED
									</span>
								{/if}
							</div>
							<div class="flex flex-wrap gap-2 text-sm text-muted-2">
								<span>{r.artist.name}</span>
								<span class="text-line">/</span>
								<span>{r.label.name}</span>
							</div>
						</div>
						<div class="text-sm text-muted flex flex-wrap justify-end gap-3.5">
							<span>{r.date ?? ''}</span>
							<span>{r.track_count ?? '—'} tr</span>
							<span>{r.country ?? ''}</span>
							<span class="min-w-[78px] text-right">{r.format ?? ''}</span>
						</div>
					</button>
				{/each}
			</div>
		{/if}
	</main>

	<aside
		class="border-border-strong bg-panel sticky top-7 flex min-w-[300px] flex-1 basis-[340px] flex-col gap-4 rounded-xl border p-5.5"
	>
		<div class="flex items-baseline justify-between gap-2.5">
			<span class="text-amber text-sm font-bold tracking-widest">LOG THIS LISTEN</span>
			<span class="text-xs text-muted-2">⏎ to save</span>
		</div>

		{#if !hasSelection}
			<div
				class="border-border-strong rounded-lg border border-dashed p-7 text-center text-sm text-muted-2 leading-relaxed"
			>
				Pick a result to fill this in.<br />Everything below stays editable.
			</div>
		{:else}
			<div class="flex flex-col gap-4.5">
				{#if !manualMode && selected}
					<div class="flex items-center gap-3.5">
						<ArtPlaceholder
							artKey={selected.artist.name}
							src={chosenArt?.thumb}
							hasArt={!!chosenArt}
							size="64px"
						/>
						<div class="flex min-w-0 flex-col gap-0.5">
							<span class="text-lg font-semibold">{selected.release.name}</span>
							<span class="text-sm text-muted-2">{selected.artist.name}</span>
							<span class="text-xs text-muted"
								>{selected.label.name} · {selected.date ?? ''} · {selected.format ?? ''}</span
							>
						</div>
					</div>
				{/if}

				{#if !manualMode && selected && (artLoading || artSearched)}
					<div class="flex flex-col gap-2">
						<div class="flex flex-wrap items-center gap-2">
							<span class="text-xs text-muted tracking-wider">ALBUM ART</span>
							{#if artLoading}
								<span class="text-xs text-muted-2 animate-pulse"
									>searching CoverArtArchive + Discogs…</span
								>
							{:else if artCandidates.length === 0}
								<span class="text-xs text-muted-2">none found — art will be fetched on save</span>
							{/if}
						</div>
						{#if artLoading}
							<div class="flex gap-1.5">
								{#each [0, 1, 2, 3] as i (i)}
									<div class="bg-field h-13 w-13 animate-pulse rounded-xs"></div>
								{/each}
							</div>
						{:else if artCandidates.length > 0}
							<div class="flex flex-col gap-1.5">
								{#each artGroups as group (group.source)}
									<div class="flex flex-wrap items-center gap-1.5">
										<span class="text-2xs text-muted-2 font-bold tracking-wider">{group.label}</span>
										{#each group.items as c (c.url)}
											<button
												class="bg-field h-13 w-13 shrink-0 cursor-pointer overflow-hidden rounded-xs border {chosenArt?.url ===
												c.url
													? 'border-amber'
													: 'border-border-strong hover:border-border-hover'}"
												aria-label={artLabel(c)}
												onclick={() => (chosenArt = c)}
											>
												<img src={c.thumb} alt="" class="h-full w-full object-cover" />
											</button>
										{/each}
									</div>
								{/each}
							</div>
						{/if}
					</div>
				{/if}

				<div class="flex flex-col gap-2">
					<div class="flex items-baseline justify-between">
						<span class="text-xs text-muted tracking-wider">RATING</span>
						<span class="text-sm text-muted">{rating}.0 / 10</span>
					</div>
					<div class="flex gap-1">
						{#each Array.from({ length: 10 }, (_, i) => i + 1) as n (n)}
							<button
								class="h-7.5 flex-1 cursor-pointer rounded text-xs {n <= rating
									? 'bg-amber text-on-amber'
									: 'bg-field text-muted border-border-strong border'}"
								onclick={() => (rating = n)}
							>
								{n}
							</button>
						{/each}
					</div>
					<span class="text-xs text-muted-2">{ratingHint(rating)}</span>
				</div>

				<label class="flex flex-col gap-1.5">
					<span class="text-xs text-muted tracking-wider">LISTENED</span>
					<input
						type="date"
						bind:value={listenDate}
						class="border-border-strong bg-field focus:border-amber rounded-md border px-2.5 py-2 text-sm outline-none"
					/>
				</label>

				<div class="flex flex-col gap-2">
					<span class="text-xs text-muted tracking-wider">GENRE</span>
					<div class="flex flex-wrap gap-1.5">
						{#each data?.all_genres ?? [] as name (name)}
							<button
								class="cursor-pointer rounded-full border px-2.5 py-1 text-xs {genres.includes(name)
									? 'border-amber-soft-border bg-amber-soft-bg text-amber-soft-fg'
									: 'border-border-strong text-muted hover:text-ink'}"
								onclick={() => toggleGenre(name)}
							>
								{name}
							</button>
						{/each}
						{#each genres.filter((g) => !(data?.all_genres ?? []).includes(g)) as name (name)}
							<button
								class="border-amber-soft-border bg-amber-soft-bg text-amber-soft-fg cursor-pointer rounded-full border px-2.5 py-1 text-xs"
								onclick={() => toggleGenre(name)}
							>
								{name} ×
							</button>
						{/each}
					</div>
					<input
						placeholder="+ add genre"
						bind:value={newGenre}
						onkeydown={(e) => e.key === 'Enter' && addGenre()}
						class="border-border-strong bg-field focus:border-amber rounded-md border px-2.5 py-2 text-sm outline-none"
					/>
				</div>

				<label class="flex flex-col gap-1.5">
					<span class="text-xs text-muted tracking-wider">NOTE — OPTIONAL</span>
					<textarea
						rows="3"
						placeholder="what did it feel like?"
						bind:value={note}
						class="border-border-strong bg-field focus:border-amber resize-y rounded-md border p-2.5 text-sm italic outline-none"
					></textarea>
				</label>

				<div class="flex items-center gap-2.5">
					<button
						class="bg-amber text-on-amber hover:bg-amber-hover flex-1 cursor-pointer rounded-lg px-4 py-2.5 text-sm font-bold tracking-wide disabled:opacity-60"
						disabled={saving}
						onclick={save}
					>
						{saved ? 'SAVED ✓' : saving ? 'SAVING…' : 'SAVE LISTEN'}
					</button>
					<button
						class="border-border-strong text-muted hover:text-ink cursor-pointer rounded-lg border px-3.5 py-2.5 text-sm"
						onclick={clearForm}
					>
						clear
					</button>
				</div>
				{#if data?.goal_nudge}
					<span class="text-center text-xs text-muted-2">{data.goal_nudge}</span>
				{/if}
			</div>
		{/if}
	</aside>
</div>
