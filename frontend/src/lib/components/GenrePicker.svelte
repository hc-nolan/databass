<script lang="ts">
	let {
		allGenres = [],
		selected = $bindable([]),
		placeholder = 'search genres…'
	}: {
		allGenres: string[];
		selected: string[];
		placeholder?: string;
	} = $props();

	type Option = { kind: 'create' | 'genre'; value: string };

	let query = $state('');
	let open = $state(false);
	let active = $state(-1);
	let root = $state<HTMLDivElement | null>(null);
	let inputEl = $state<HTMLInputElement | null>(null);

	const normalizedQuery = $derived(query.trim().toLowerCase());

	const matches = $derived(
		allGenres.filter((g) => !selected.includes(g) && g.toLowerCase().includes(normalizedQuery))
	);

	const canCreate = $derived.by(() => {
		const q = query.trim();
		if (!q) return false;
		const lower = q.toLowerCase();
		return (
			!allGenres.some((g) => g.toLowerCase() === lower) &&
			!selected.some((g) => g.toLowerCase() === lower)
		);
	});

	const options = $derived.by<Option[]>(() => {
		const out: Option[] = [];
		for (const g of matches.slice(0, 100)) out.push({ kind: 'genre', value: g });
		// Existing genres are offered first so Enter selects a real match
		// before the "create" option can win.
		if (canCreate) out.push({ kind: 'create', value: query.trim() });
		return out;
	});

	function addGenre(name: string) {
		const value = name.trim();
		if (!value) return;
		if (!selected.some((g) => g.toLowerCase() === value.toLowerCase())) {
			selected = [...selected, value];
		}
		query = '';
		active = -1;
		inputEl?.focus();
	}

	function removeGenre(name: string) {
		selected = selected.filter((g) => g !== name);
	}

	function choose(option: Option) {
		addGenre(option.value);
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'ArrowDown') {
			if (!open) {
				open = true;
				return;
			}
			event.preventDefault();
			active = options.length ? Math.min(active + 1, options.length - 1) : -1;
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			active = Math.max(active - 1, 0);
		} else if (event.key === 'Enter') {
			event.preventDefault();
			if (open && active >= 0 && active < options.length) choose(options[active]);
			else if (options.length) choose(options[0]);
		} else if (event.key === 'Escape') {
			open = false;
			active = -1;
		} else if (event.key === 'Backspace' && !query && selected.length) {
			removeGenre(selected[selected.length - 1]);
		}
	}

	$effect(() => {
		if (!open) return;
		const onDocMouseDown = (event: MouseEvent) => {
			if (root && !root.contains(event.target as Node)) open = false;
		};
		document.addEventListener('mousedown', onDocMouseDown);
		return () => document.removeEventListener('mousedown', onDocMouseDown);
	});

	// keep the highlight valid as the option list changes
	$effect(() => {
		void options;
		if (active >= options.length) active = options.length - 1;
	});
</script>

<div class="relative flex flex-col gap-2" bind:this={root}>
	{#if selected.length}
		<div class="flex flex-wrap gap-1.5">
			{#each selected as name (name)}
				<button
					type="button"
					class="cursor-pointer rounded-full border border-amber-soft-border bg-amber-soft-bg px-2.5 py-1 text-xs text-amber-soft-fg"
					onclick={() => removeGenre(name)}
				>
					{name} ×
				</button>
			{/each}
		</div>
	{/if}

	<input
		bind:this={inputEl}
		bind:value={query}
		placeholder={selected.length ? 'add another…' : placeholder}
		autocomplete="off"
		role="combobox"
		aria-expanded={open}
		aria-controls="genre-listbox"
		aria-autocomplete="list"
		aria-activedescendant={open && active >= 0 ? `genre-option-${active}` : undefined}
		onfocus={() => (open = true)}
		onclick={() => (open = true)}
		oninput={() => (open = true)}
		onkeydown={onKeydown}
		class="rounded-md border border-border-strong bg-field px-2.5 py-2 text-sm outline-none focus:border-amber"
	/>

	{#if open && options.length > 0}
		<div
			id="genre-listbox"
			role="listbox"
			class="absolute top-full left-0 z-20 mt-1 flex max-h-56 w-full flex-col gap-0.5 overflow-y-auto rounded-lg border border-border bg-panel p-1 shadow-lg"
		>
			{#each options as option, i (option.kind + option.value)}
				<button
					type="button"
					id="genre-option-{i}"
					role="option"
					aria-selected={i === active}
					class="flex w-full cursor-pointer items-center justify-between gap-2 rounded px-2.5 py-1.5 text-left text-sm hover:bg-hover {i ===
					active
						? 'bg-hover text-ink'
						: 'text-ink-3'}"
					onmouseenter={() => (active = i)}
					onclick={() => choose(option)}
				>
					{#if option.kind === 'create'}
						<span>create <span class="text-amber">“{option.value}”</span></span>
						<span class="text-2xs text-muted-2">new</span>
					{:else}
						<span>{option.value}</span>
					{/if}
				</button>
			{/each}
		</div>
	{/if}
</div>
