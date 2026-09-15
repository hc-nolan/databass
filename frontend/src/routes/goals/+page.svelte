<script lang="ts">
	import { onMount } from 'svelte';
	import { apiGet, apiPost } from '$lib/api';
	import type { GoalsData } from '$lib/types';
	import { headerState } from '$lib/chrome.svelte';
	import { daysBetween } from '$lib/format';

	let data = $state<GoalsData | null>(null);
	let amount = $state('100');
	let type = $state('release');
	let end = $state('');
	let submitting = $state(false);
	let submitError = $state('');

	async function load() {
		data = await apiGet<GoalsData>('/goals');
		amount = String(data.default_amount);
		end = data.default_end;
		type = data.goal_types[0]?.value ?? 'release';
	}

	onMount(load);

	$effect(() => {
		headerState.counter = counterSnippet;
	});

	const feasibility = $derived.by(() => {
		if (!data) return null;
		const amt = parseInt(amount, 10) || 0;
		const days = Math.max(1, daysBetween(data.today, end || data.today));
		const rate = amt / days;
		const pace = data.current_pace || 0.01;
		const ratio = rate / pace;
		if (ratio <= 0.85) {
			const etaDays = pace ? amt / pace : 0;
			const eta = new Date(Date.parse(data.today) + etaDays * 86400000).toISOString().slice(0, 10);
			return {
				tone: 'cyan' as const,
				rate,
				text: `Comfortable. That's below your ${pace.toFixed(2)} / day average — you'd hit it around ${eta} at your current pace.`
			};
		} else if (ratio <= 1.25) {
			return {
				tone: 'amber' as const,
				rate,
				text: `Realistic. Roughly your current pace of ${pace.toFixed(2)} / day, sustained for ${days} days.`
			};
		} else {
			return {
				tone: 'red' as const,
				rate,
				text: `Ambitious. That's ${ratio.toFixed(1)}× your current pace — you'd need to log ${Math.ceil(
					rate - pace
				)} more per day than you do now.`
			};
		}
	});

	function applyPreset(preset: { amount: number; end: string }) {
		amount = String(preset.amount);
		end = preset.end;
	}

	async function createGoal() {
		if (!data) return;
		submitting = true;
		submitError = '';
		try {
			await apiPost('/goals', {
				start: data.today,
				end,
				type,
				amount: parseInt(amount, 10) || 0
			});
			await load();
		} catch (e) {
			submitError = e instanceof Error ? e.message : 'Failed to create goal';
		} finally {
			submitting = false;
		}
	}

	function toneClasses(tone: 'ink' | 'amber' | 'cyan' | 'red') {
		return {
			ink: 'text-ink',
			amber: 'text-amber',
			cyan: 'text-cyan',
			red: 'text-danger-text'
		}[tone];
	}

	function toneBorder(tone: 'cyan' | 'amber' | 'red') {
		return {
			cyan: 'border-border-strong',
			amber: 'border-amber-soft-border',
			red: 'border-border-strong'
		}[tone];
	}
</script>

{#snippet counterSnippet()}{/snippet}

<div class="mx-auto flex max-w-[1100px] flex-col gap-6.5 p-7">
	{#if data?.active_goal}
		{@const g = data.active_goal}
		<section class="border-border bg-panel flex flex-col gap-5 rounded-xl border p-6.5">
			<div class="flex flex-wrap items-baseline gap-3">
				<span class="text-amber text-xs font-bold tracking-widest">ACTIVE GOAL</span>
				<span
					class="rounded-full px-2.5 py-0.5 text-[10.5px] font-bold tracking-wide {g.on_track
						? 'bg-cyan-soft-bg text-cyan-soft-fg'
						: 'bg-red-soft-bg text-red-soft-fg'}"
				>
					{g.status}
				</span>
				<span class="ml-auto text-sm text-muted">{g.window}</span>
			</div>

			<div class="flex flex-wrap items-baseline gap-2.5">
				<span class="text-4xl leading-none font-medium tracking-tight">{g.actual}</span>
				<span class="text-lg text-muted">/ {g.target} {g.type_label}</span>
				<span class="text-sm text-muted">{g.percent}% complete</span>
			</div>

			<div class="flex flex-col gap-2">
				<div class="bg-border relative h-4 overflow-hidden rounded-lg">
					<div class="bg-amber absolute inset-y-0 left-0 rounded-lg" style="width:{g.progress_w}%"></div>
					<div class="absolute top-0 bottom-0 w-0.5 bg-ink" style="left:{g.pace_w}%"></div>
				</div>
				<div class="flex flex-wrap justify-between gap-2.5 text-sm text-muted">
					<span>{g.progress_label}</span>
					<span>{g.pace_label}</span>
				</div>
			</div>

			<div class="border-border bg-border grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-px overflow-hidden rounded-lg border">
				{#each g.metrics as m (m.label)}
					<div class="bg-panel flex flex-col gap-1 p-3.5">
						<span class="text-2xs text-muted tracking-wider">{m.label}</span>
						<span class="text-lg font-semibold tracking-tight {toneClasses(m.tone)}">{m.value}</span>
						<span class="text-xs text-muted">{m.sub}</span>
					</div>
				{/each}
			</div>

			<p class="text-md text-ink-2 text-pretty">{g.projection}</p>
		</section>
	{:else if data}
		<section class="border-border bg-panel flex flex-col items-center gap-2 rounded-xl border p-8 text-center">
			<span class="text-amber text-xs font-bold tracking-widest">NO ACTIVE GOAL</span>
			<p class="text-sm text-muted">Set one below to start tracking progress.</p>
		</section>
	{/if}

	{#if data}
		<section class="border-border bg-panel flex flex-col gap-4 rounded-xl border p-5.5">
			<div class="flex flex-wrap items-baseline gap-3">
				<span class="text-amber text-xs font-bold tracking-widest">SET A NEW GOAL</span>
				<span class="text-sm text-muted">the numbers update as you type</span>
			</div>

			<div class="flex flex-wrap items-end gap-3">
				<label class="flex min-w-[110px] flex-1 flex-col gap-1.5">
					<span class="text-2xs text-muted tracking-wider">AMOUNT</span>
					<input
						type="number"
						min="1"
						bind:value={amount}
						class="border-border-strong bg-field focus:border-amber rounded-lg border px-3 py-2.5 text-sm outline-none"
					/>
				</label>
				<label class="flex min-w-[130px] flex-1 flex-col gap-1.5">
					<span class="text-2xs text-muted tracking-wider">OF</span>
					<div class="border-border-strong flex gap-1 rounded-lg border p-0.5">
						{#each data.goal_types as t (t.value)}
							<button
								class="flex-1 cursor-pointer rounded-md px-2.5 py-1.5 text-sm {type === t.value
									? 'bg-hover text-ink'
									: 'text-muted'}"
								onclick={() => (type = t.value)}
							>
								{t.label}
							</button>
						{/each}
					</div>
				</label>
				<label class="flex min-w-[140px] flex-1 flex-col gap-1.5">
					<span class="text-2xs text-muted tracking-wider">BY</span>
					<input
						type="date"
						bind:value={end}
						class="border-border-strong bg-field focus:border-amber rounded-lg border px-3 py-2.5 text-sm outline-none"
					/>
				</label>
				<button
					class="bg-amber text-on-amber hover:bg-amber-hover cursor-pointer rounded-lg px-5 py-2.5 text-sm font-bold tracking-wide disabled:opacity-50"
					disabled={submitting}
					onclick={createGoal}
				>
					{submitting ? 'CREATING…' : 'CREATE GOAL'}
				</button>
			</div>

			{#if submitError}
				<p class="text-danger-text text-sm">{submitError}</p>
			{/if}

			{#if feasibility}
				<div class="border-border/70 flex flex-wrap items-center gap-2.5 rounded-lg border p-3.5 {toneBorder(feasibility.tone)}">
					<span class="text-lg font-semibold tracking-tight {toneClasses(feasibility.tone)}">
						{feasibility.rate.toFixed(2)} / day
					</span>
					<span class="text-ink-2 min-w-[240px] flex-1 text-sm text-pretty">{feasibility.text}</span>
				</div>
			{/if}

			<div class="flex flex-wrap items-center gap-2">
				<span class="text-xs text-muted">try:</span>
				{#each data.goal_presets as p (p.label)}
					<button
						class="border-border-strong text-ink-2 hover:border-border-hover cursor-pointer rounded-full border px-2.5 py-1 text-xs"
						onclick={() => applyPreset(p)}
					>
						{p.label}
					</button>
				{/each}
			</div>
		</section>

		{#if data.past_goals.length > 0}
			<section class="flex flex-col gap-3.5">
				<span class="text-amber text-xs font-bold tracking-widest">PAST GOALS</span>
				<div class="flex flex-col gap-2">
					{#each data.past_goals as g (g.title + g.window)}
						<div
							class="border-border bg-panel grid grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_auto] items-center gap-4.5 rounded-lg border px-4 py-3.5"
						>
							<div class="flex min-w-0 flex-col gap-0.5">
								<span class="text-md font-medium">{g.title}</span>
								<span class="text-sm text-muted">{g.window}</span>
							</div>
							<div class="flex min-w-0 flex-col gap-1.5">
								<div class="bg-line h-[5px] overflow-hidden rounded-sm">
									<div
										class="h-[5px] rounded-sm {g.tone === 'cyan' ? 'bg-cyan' : 'bg-red'}"
										style="width:{g.w}%"
									></div>
								</div>
								<span class="text-ink-3 text-sm">{g.result}</span>
							</div>
							<span
								class="rounded-full px-2.5 py-0.5 text-[10.5px] font-bold tracking-wide {g.badge ===
								'COMPLETE'
									? 'bg-cyan-soft-bg text-cyan-soft-fg'
									: 'bg-red-soft-bg text-red-soft-fg'}"
							>
								{g.badge}
							</span>
						</div>
					{/each}
				</div>
			</section>
		{/if}
	{/if}
</div>
