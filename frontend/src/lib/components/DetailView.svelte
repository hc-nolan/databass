<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiGet, apiPut, apiPost, apiDelete } from '$lib/api';
	import type { DetailView, ReleaseEditData, EntityEditData, MissingRelease } from '$lib/types';
	import { headerState } from '$lib/chrome.svelte';
	import { imageSrc, ratingHint, toDateInputValue } from '$lib/format';
	import ArtPlaceholder from './ArtPlaceholder.svelte';
	import FactStrip from './FactStrip.svelte';
	import Rail from './Rail.svelte';
	import Modal from './Modal.svelte';
	import ConfirmDialog from './ConfirmDialog.svelte';

	let { kind, id }: { kind: 'release' | 'artist' | 'label'; id: number } = $props();

	let detail = $state<DetailView | null>(null);
	let missing = $state<MissingRelease[]>([]);
	let missingLoading = $state(false);
	let editOpen = $state(false);
	let deleteOpen = $state(false);
	let relistening = $state(false);
	let relistened = $state(false);

	let releaseEdit = $state<ReleaseEditData | null>(null);
	let entityEdit = $state<EntityEditData | null>(null);
	let genresText = $state('');
	let collabText = $state('');
	let saving = $state(false);
	let saveError = $state('');

	let newEntryText = $state('');
	let addingEntry = $state(false);
	let editingEntryId = $state<number | null>(null);
	let editingEntryText = $state('');

	async function load() {
		detail = await apiGet<DetailView>(`/${kind}/${id}`);
		relistened = false;
	}

	async function loadMissing() {
		missing = [];
		if (kind !== 'artist') return;
		missingLoading = true;
		try {
			const res = await apiGet<{ missing: MissingRelease[] }>(`/artist/${id}/missing`);
			missing = res.missing;
		} finally {
			missingLoading = false;
		}
	}

	$effect(() => {
		id;
		kind;
		load();
		loadMissing();
	});

	$effect(() => {
		headerState.counter = counterSnippet;
	});

	async function openEdit() {
		saveError = '';
		if (kind === 'release') {
			releaseEdit = await apiGet<ReleaseEditData>(`/release/${id}/edit`);
			genresText = releaseEdit.genres.join(', ');
			collabText = releaseEdit.collab_artists.join(', ');
		} else {
			entityEdit = await apiGet<EntityEditData>(`/${kind}/${id}/edit`);
			entityEdit.begin = toDateInputValue(entityEdit.begin);
			entityEdit.end = toDateInputValue(entityEdit.end);
		}
		editOpen = true;
	}

	async function saveEdit() {
		saving = true;
		saveError = '';
		try {
			if (kind === 'release' && releaseEdit) {
				detail = await apiPut<DetailView>(`/release/${id}`, {
					year: releaseEdit.year,
					listen_date: releaseEdit.listen_date,
					rating: releaseEdit.rating,
					main_genre: releaseEdit.main_genre,
					country: releaseEdit.country,
					image: releaseEdit.image,
					genres: genresText
						.split(',')
						.map((g) => g.trim())
						.filter(Boolean),
					collab_artists: collabText
						.split(',')
						.map((c) => c.trim())
						.filter(Boolean)
				});
			} else if (entityEdit) {
				detail = await apiPut<DetailView>(`/${kind}/${id}`, {
					start: entityEdit.begin,
					end: entityEdit.end,
					country: entityEdit.country,
					image: entityEdit.image
				});
			}
			editOpen = false;
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to save';
		} finally {
			saving = false;
		}
	}

	async function doDelete() {
		if (!detail?.delete_type || detail.delete_id == null) return;
		await apiDelete(`/${detail.delete_type}/${detail.delete_id}`);
		goto(detail.crumb_href);
	}

	async function relisten() {
		relistening = true;
		try {
			detail = await apiPost<DetailView>(`/release/${id}/relisten`);
			relistened = true;
		} finally {
			relistening = false;
		}
	}

	async function addEntry() {
		if (!newEntryText.trim()) return;
		addingEntry = true;
		try {
			detail = await apiPost<DetailView>(`/release/${id}/reviews`, { text: newEntryText.trim() });
			newEntryText = '';
		} finally {
			addingEntry = false;
		}
	}

	function startEditEntry(entryId: number, text: string) {
		editingEntryId = entryId;
		editingEntryText = text;
	}

	async function saveEntry(entryId: number) {
		detail = await apiPut<DetailView>(`/release/${id}/reviews/${entryId}`, {
			text: editingEntryText
		});
		editingEntryId = null;
	}
</script>

{#snippet counterSnippet()}{/snippet}

{#if detail}
	<div class="mx-auto flex max-w-[1240px] flex-col gap-6 p-7">
		<div class="flex flex-wrap items-center gap-2 text-sm text-muted">
			<a href="/browse/{detail.crumb_label}" class="hover:text-ink">browse</a>
			<span class="text-line">/</span>
			<a href="/browse/{detail.crumb_label}" class="hover:text-ink">{detail.crumb_label}</a>
			<span class="text-line">/</span>
			<span class="text-ink-2">{detail.name}</span>
		</div>

		<section class="flex flex-wrap items-start gap-6.5">
			<ArtPlaceholder
				artKey={detail.art_key}
				hasArt={detail.has_art}
				src={imageSrc(kind, id)}
				size="212px"
				radius="rounded-lg"
				textClass="text-lg font-bold tracking-widest text-muted"
			/>

			<div class="flex min-w-[280px] flex-1 basis-[380px] flex-col gap-3.5">
				<div class="flex flex-col gap-1.5">
					<span class="text-amber text-xs font-bold tracking-widest">{detail.eyebrow}</span>
					<h1 class="text-3xl leading-tight font-bold tracking-tight text-pretty">{detail.name}</h1>
					<div class="flex flex-wrap items-center gap-2.5 text-base">
						{#each detail.links as l (l.name)}
							{#if l.href}
								<a href={l.href} class="text-ink-2 border-b border-border-strong">{l.name}</a>
							{:else}
								<span class="text-ink-2">{l.name}</span>
							{/if}
						{/each}
						{#if detail.subline}
							<span class="text-sm text-muted">{detail.subline}</span>
						{/if}
					</div>
				</div>

				{#if detail.tags.length > 0}
					<div class="flex flex-wrap gap-1.5">
						{#each detail.tags as t (t)}
							<span class="border-border-strong text-ink-3 rounded-full border px-2.5 py-0.5 text-xs">
								{t}
							</span>
						{/each}
					</div>
				{/if}

				<FactStrip facts={detail.facts} />

				<div class="flex flex-wrap items-center gap-2">
					{#if detail.is_release}
						<button
							class="bg-amber text-on-amber hover:bg-amber-hover cursor-pointer rounded-lg px-4 py-2.5 text-sm font-bold tracking-wide disabled:opacity-50"
							disabled={relistening}
							onclick={relisten}
						>
							{relistened ? 'LOGGED AGAIN ✓' : 'LOG ANOTHER LISTEN'}
						</button>
					{/if}
					<button
						class="border-border-strong text-ink-3 hover:border-border-hover hover:text-ink cursor-pointer rounded-lg border px-3.5 py-2.5 text-sm"
						onclick={openEdit}
					>
						edit
					</button>
					{#if detail.show_delete}
						<button
							class="border-border-strong text-danger-text hover:border-red cursor-pointer rounded-lg border px-3.5 py-2.5 text-sm"
							onclick={() => (deleteOpen = true)}
						>
							delete
						</button>
					{/if}
					{#if detail.source_href}
						<a href={detail.source_href} target="_blank" rel="noreferrer" class="text-sm text-muted border-b border-border-strong ml-1">
							view on MusicBrainz ↗
						</a>
					{/if}
				</div>
			</div>
		</section>

		{#if detail.is_release}
			<section class="flex flex-wrap items-start gap-5">
				<div class="border-border bg-panel flex min-w-[300px] flex-1 basis-[420px] flex-col gap-3.5 rounded-xl border p-5.5">
					<div class="flex flex-wrap items-baseline justify-between gap-2.5">
						<span class="text-amber text-xs font-bold tracking-widest">DIARY</span>
						<span class="text-sm text-muted">{detail.diary_meta}</span>
					</div>
					<div class="flex flex-col gap-3.5">
						{#each detail.entries ?? [] as e (e.id)}
							<div class="border-amber-soft-border flex flex-col gap-1.5 border-l-2 pl-3.5">
								<div class="flex flex-wrap items-baseline gap-2.5">
									<span class="text-ink-3 text-sm">{e.date}</span>
									{#if editingEntryId === e.id}
										<button class="text-amber text-xs" onclick={() => saveEntry(e.id)}>save</button>
										<button class="text-xs text-muted" onclick={() => (editingEntryId = null)}>cancel</button>
									{:else}
										<button
											class="text-xs text-muted hover:text-ink cursor-pointer"
											onclick={() => startEditEntry(e.id, e.text)}
										>
											edit
										</button>
									{/if}
								</div>
								{#if editingEntryId === e.id}
									<textarea
										rows="3"
										bind:value={editingEntryText}
										class="border-border-strong bg-field focus:border-amber rounded-lg border p-2.5 text-sm italic outline-none"
									></textarea>
								{:else}
									<p class="text-md text-ink-2 text-pretty italic">{e.text}</p>
								{/if}
							</div>
						{/each}
					</div>
					<textarea
						rows="3"
						placeholder="add to this record's diary…"
						bind:value={newEntryText}
						class="border-border-strong bg-field focus:border-amber rounded-lg border p-2.5 text-sm italic outline-none"
					></textarea>
					<button
						class="border-border-strong text-ink-2 hover:border-border-hover w-fit cursor-pointer rounded-lg border px-3.5 py-2 text-sm disabled:opacity-50"
						disabled={addingEntry}
						onclick={addEntry}
					>
						save entry
					</button>
				</div>

				<div class="border-border bg-panel flex min-w-[260px] flex-1 basis-[280px] flex-col gap-3 rounded-xl border p-5.5">
					<span class="text-amber text-xs font-bold tracking-widest">IN CONTEXT</span>
					<div class="grid grid-cols-[1fr_auto] gap-x-3 gap-y-2.5 text-sm">
						{#each detail.context ?? [] as c (c.label)}
							<span class="text-ink-3">{c.label}</span>
							<span class="text-ink-2 text-right">{c.value}</span>
						{/each}
					</div>
				</div>
			</section>
		{/if}

		{#if kind === 'artist' && (missingLoading || missing.length > 0)}
			<section class="flex flex-col gap-3.5">
				<div class="flex flex-wrap items-baseline gap-3">
					<span class="text-amber text-sm font-bold tracking-widest">MISSING</span>
					<span class="text-sm text-muted">
						{missingLoading ? 'checking MusicBrainz…' : `${missing.length} not logged yet`}
					</span>
				</div>
				{#if !missingLoading}
					<div class="grid grid-cols-[repeat(auto-fill,minmax(146px,1fr))] gap-4">
						{#each missing as m (m.href)}
							<a
								href={m.href}
								class="border-border-strong hover:border-border-hover flex min-w-0 flex-col gap-0.5 rounded-lg border border-dashed p-3"
							>
								<span class="text-md leading-tight text-pretty">{m.name}</span>
								<span class="text-sm text-muted">{m.year ?? '—'}</span>
							</a>
						{/each}
					</div>
				{/if}
			</section>
		{/if}

		{#each detail.rails as rail (rail.title)}
			<Rail {rail} />
		{/each}
	</div>

	<ConfirmDialog
		bind:open={deleteOpen}
		title="Delete this {kind}?"
		message="This can't be undone."
		confirmLabel="delete"
		onConfirm={doDelete}
	/>

	<Modal bind:open={editOpen} title="Edit {kind}">
		{#snippet children()}
			{#if kind === 'release' && releaseEdit}
				<div class="flex flex-col gap-3.5">
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">YEAR</span>
						<input
							type="number"
							bind:value={releaseEdit.year}
							class="border-border-strong bg-field rounded-lg border px-3 py-2 text-sm outline-none"
						/>
					</label>
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">LISTENED</span>
						<input
							type="date"
							bind:value={releaseEdit.listen_date}
							class="border-border-strong bg-field rounded-lg border px-3 py-2 text-sm outline-none"
						/>
					</label>
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">RATING</span>
						<input
							type="range"
							min="0"
							max="100"
							bind:value={releaseEdit.rating}
							class="w-full"
						/>
						<span class="text-xs text-muted">{ratingHint(Math.round(releaseEdit.rating / 10))}</span>
					</label>
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">MAIN GENRE</span>
						<input
							bind:value={releaseEdit.main_genre}
							class="border-border-strong bg-field rounded-lg border px-3 py-2 text-sm outline-none"
						/>
					</label>
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">GENRES (comma separated)</span>
						<input
							bind:value={genresText}
							class="border-border-strong bg-field rounded-lg border px-3 py-2 text-sm outline-none"
						/>
					</label>
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">COLLAB ARTISTS (comma separated)</span>
						<input
							bind:value={collabText}
							class="border-border-strong bg-field rounded-lg border px-3 py-2 text-sm outline-none"
						/>
					</label>
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">COUNTRY</span>
						<input
							bind:value={releaseEdit.country}
							class="border-border-strong bg-field rounded-lg border px-3 py-2 text-sm outline-none"
						/>
					</label>
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">COVER IMAGE URL</span>
						<input
							bind:value={releaseEdit.image}
							class="border-border-strong bg-field rounded-lg border px-3 py-2 text-sm outline-none"
						/>
					</label>
				</div>
			{:else if entityEdit}
				<div class="flex flex-col gap-3.5">
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">NAME</span>
						<input
							value={entityEdit.name}
							disabled
							class="border-border-strong bg-field rounded-lg border px-3 py-2 text-sm opacity-60 outline-none"
						/>
					</label>
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">
							{kind === 'artist' ? 'BEGIN' : 'FOUNDED'}
						</span>
						<input
							type="date"
							bind:value={entityEdit.begin}
							class="border-border-strong bg-field rounded-lg border px-3 py-2 text-sm outline-none"
						/>
					</label>
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">
							{kind === 'artist' ? 'END' : 'CLOSED'}
						</span>
						<input
							type="date"
							bind:value={entityEdit.end}
							class="border-border-strong bg-field rounded-lg border px-3 py-2 text-sm outline-none"
						/>
					</label>
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">COUNTRY</span>
						<input
							bind:value={entityEdit.country}
							class="border-border-strong bg-field rounded-lg border px-3 py-2 text-sm outline-none"
						/>
					</label>
					<label class="flex flex-col gap-1.5">
						<span class="text-2xs text-muted tracking-wider">IMAGE URL</span>
						<input
							bind:value={entityEdit.image}
							class="border-border-strong bg-field rounded-lg border px-3 py-2 text-sm outline-none"
						/>
					</label>
				</div>
			{/if}
			{#if saveError}
				<p class="text-danger-text text-sm">{saveError}</p>
			{/if}
		{/snippet}
		{#snippet footer()}
			<button
				class="border-border-strong text-ink-3 hover:border-border-hover cursor-pointer rounded-lg border px-4 py-2 text-sm"
				onclick={() => (editOpen = false)}
			>
				cancel
			</button>
			<button
				class="bg-amber text-on-amber hover:bg-amber-hover cursor-pointer rounded-lg px-4 py-2 text-sm font-bold disabled:opacity-50"
				disabled={saving}
				onclick={saveEdit}
			>
				{saving ? 'saving…' : 'save'}
			</button>
		{/snippet}
	</Modal>
{/if}
