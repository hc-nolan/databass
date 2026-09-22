<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import { apiGet, apiPost } from '$lib/api';
	import type {
		ExploreFilterRow,
		ExploreFilterState,
		ExploreOptions,
		ExploreResponse,
		ExploreSpec
	} from '$lib/types';
	import { headerState } from '$lib/chrome.svelte';
	import StatsTabs from '$lib/components/StatsTabs.svelte';
	import ExploreQueryBuilder from '$lib/components/ExploreQueryBuilder.svelte';
	import ExploreChart from '$lib/components/ExploreChart.svelte';

	let options = $state<ExploreOptions | null>(null);
	let rows = $state<ExploreFilterState[]>([]);
	let groupBy = $state('artist');
	let metric = $state('count');
	let minItems = $state(1);
	let order = $state<'desc' | 'asc'>('desc');
	let limit = $state(15);

	let result = $state<ExploreResponse | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);

	// Monotonic token so a slow earlier response can't overwrite a fresher one.
	let runSeq = 0;

	const FILTER_OPS = ['contains', 'eq', 'overlaps', 'between', 'gte', 'lte'];

	// --- spec <-> UI state ---

	function buildSpec(): ExploreSpec {
		return {
			group_by: groupBy,
			metric,
			min_items: minItems,
			order,
			limit,
			filters: rowsToFilters(rows)
		};
	}

	function rowsToFilters(list: ExploreFilterState[]): ExploreFilterRow[] {
		const out: ExploreFilterRow[] = [];
		for (const row of list) {
			if (row.kind === 'text') {
				const v = row.text?.trim();
				if (v) out.push({ field: row.field, op: 'contains', value: v });
			} else if (row.kind === 'enum') {
				if (row.enumValue) out.push({ field: row.field, op: 'eq', value: row.enumValue });
			} else if (row.kind === 'years') {
				const lo = parseInt(row.lo ?? '', 10);
				const hi = parseInt(row.hi ?? '', 10);
				if (!Number.isNaN(lo) && !Number.isNaN(hi)) {
					out.push({ field: row.field, op: 'overlaps', value: [lo, hi] });
				}
			} else if (row.kind === 'range') {
				const lo = row.lo !== undefined && row.lo !== '' ? parseInt(row.lo, 10) : NaN;
				const hi = row.hi !== undefined && row.hi !== '' ? parseInt(row.hi, 10) : NaN;
				if (!Number.isNaN(lo) && !Number.isNaN(hi)) {
					out.push({ field: row.field, op: 'between', value: [lo, hi] });
				} else if (!Number.isNaN(lo)) {
					out.push({ field: row.field, op: 'gte', value: lo });
				} else if (!Number.isNaN(hi)) {
					out.push({ field: row.field, op: 'lte', value: hi });
				}
			}
		}
		return out;
	}

	function filtersToRows(filters: ExploreFilterRow[]): ExploreFilterState[] {
		if (!options) return [];
		const byField = new Map(options.fields.map((f) => [f.value, f.kind]));
		return filters
			.filter(
				(f) => f && typeof f === 'object' && byField.has(f.field) && FILTER_OPS.includes(f.op)
			)
			.map((f): ExploreFilterState => {
				const kind = byField.get(f.field)!;
				if (kind === 'text') return { field: f.field, kind, text: String(f.value) };
				if (kind === 'enum') return { field: f.field, kind, enumValue: String(f.value) };
				if (kind === 'years') {
					const [lo, hi] = (Array.isArray(f.value) ? f.value : [null, null]) as [
						number | null,
						number | null
					];
					return { field: f.field, kind, lo: lo?.toString() ?? '', hi: hi?.toString() ?? '' };
				}
				// range
				if (f.op === 'between') {
					const [lo, hi] = f.value as [number | null, number | null];
					return {
						field: f.field,
						kind,
						lo: lo === null ? '' : String(lo),
						hi: hi === null ? '' : String(hi)
					};
				}
				if (f.op === 'gte') return { field: f.field, kind, lo: String(f.value) };
				if (f.op === 'lte') return { field: f.field, kind, hi: String(f.value) };
				return { field: f.field, kind };
			});
	}

	function applySpec(spec: ExploreSpec | null) {
		if (!options) return;
		const defaults = options.defaults;
		if (!spec || typeof spec !== 'object') {
			groupBy = defaults.group_by;
			metric = defaults.metric;
			minItems = defaults.min_items;
			order = defaults.order;
			limit = defaults.limit;
			rows = [];
			return;
		}
		groupBy = options.group_bys.some((g) => g.value === spec.group_by)
			? spec.group_by
			: defaults.group_by;
		metric = options.metrics.some((m) => m.value === spec.metric) ? spec.metric : defaults.metric;
		minItems = clampInt(spec.min_items, 1, 1000, defaults.min_items);
		order = spec.order === 'asc' ? 'asc' : 'desc';
		limit = clampInt(spec.limit, 1, 50, defaults.limit);
		rows = filtersToRows(Array.isArray(spec.filters) ? spec.filters : []);
	}

	function clampInt(v: unknown, lo: number, hi: number, fallback: number): number {
		const n = typeof v === 'number' ? v : parseInt(String(v), 10);
		if (Number.isNaN(n)) return fallback;
		return Math.max(lo, Math.min(hi, n));
	}

	// --- URL encoding (UTF-8 -> base64url) ---

	function encodeSpec(spec: ExploreSpec): string {
		const bytes = new TextEncoder().encode(JSON.stringify(spec));
		let binary = '';
		for (const b of bytes) binary += String.fromCharCode(b);
		return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
	}

	function decodeSpec(raw: string): ExploreSpec | null {
		try {
			const binary = atob(raw.replace(/-/g, '+').replace(/_/g, '/'));
			const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
			const spec: unknown = JSON.parse(new TextDecoder().decode(bytes));
			return spec && typeof spec === 'object' && !Array.isArray(spec)
				? (spec as ExploreSpec)
				: null;
		} catch {
			return null;
		}
	}

	// --- run + URL sync ---

	async function run() {
		const seq = ++runSeq;
		loading = true;
		error = null;
		try {
			const res = await apiPost<ExploreResponse>('/explore', buildSpec());
			if (seq !== runSeq) return; // stale response — a newer run is in flight
			result = res;
		} catch (e) {
			if (seq !== runSeq) return;
			error = e instanceof Error ? e.message : String(e);
		} finally {
			if (seq === runSeq) loading = false;
		}
	}

	function syncUrl() {
		const q = encodeSpec(buildSpec());
		const target = resolve(`/stats/explore?q=${q}` as '/stats/explore');
		if (page.url.pathname + page.url.search !== target) {
			goto(target, {
				replaceState: true,
				keepFocus: true,
				invalidateAll: false,
				noScroll: true
			});
		}
	}

	$effect(() => {
		void rows;
		void groupBy;
		void metric;
		void minItems;
		void order;
		void limit;
		if (!options) return;
		const timer = setTimeout(() => {
			syncUrl();
			run();
		}, 250);
		return () => clearTimeout(timer);
	});

	onMount(async () => {
		try {
			options = await apiGet<ExploreOptions>('/explore/options');
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			return;
		}
		const q = page.url.searchParams.get('q');
		applySpec(q ? decodeSpec(q) : null);
	});

	$effect(() => {
		headerState.counter = counterSnippet;
	});
</script>

{#snippet counterSnippet()}
	{#if result}
		<span>{result.meta.total_matched.toLocaleString()} matched</span>
	{/if}
{/snippet}

<div class="flex flex-col gap-5 p-7">
	<div class="flex flex-wrap items-center gap-4">
		<StatsTabs />
	</div>

	{#if options}
		<ExploreQueryBuilder
			bind:rows
			bind:groupBy
			bind:metric
			bind:minItems
			bind:order
			bind:limit
			{options}
		/>
	{/if}

	{#if error}
		<p class="text-sm text-red">Hmm, that query failed: {error}</p>
	{:else if result && result.rows.length === 0}
		<section class="rounded-xl border border-border bg-panel p-5">
			<p class="py-8 text-center text-sm text-muted-2">No releases match these filters.</p>
		</section>
	{:else if result}
		<section class="flex flex-col gap-4 rounded-xl border border-border bg-panel p-5">
			<div class="flex flex-wrap items-baseline justify-between gap-2.5">
				<span class="text-xs font-bold tracking-widest text-amber">
					{result.meta.metric_label.toUpperCase()} BY {result.meta.dimension_label.toUpperCase()}
				</span>
				<span class="text-sm text-muted">
					{result.meta.total_matched.toLocaleString()} release{result.meta.total_matched === 1
						? ''
						: 's'} matched · showing {result.rows.length}
				</span>
			</div>
			<ExploreChart data={result} />
		</section>
	{:else if loading}
		<p class="py-8 text-center text-sm text-muted-2">Crunching numbers…</p>
	{/if}
</div>
