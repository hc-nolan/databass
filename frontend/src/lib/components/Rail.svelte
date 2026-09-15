<script lang="ts">
	import type { Rail } from '$lib/types';
	import ArtPlaceholder from './ArtPlaceholder.svelte';
	import { imageSrc } from '$lib/format';

	let { rail }: { rail: Rail } = $props();
</script>

<section class="flex flex-col gap-3.5">
	<div class="flex flex-wrap items-baseline gap-3">
		<span class="text-amber text-sm font-bold tracking-widest">{rail.title}</span>
		<span class="text-sm text-muted">{rail.note}</span>
	</div>
	<div class="grid grid-cols-[repeat(auto-fill,minmax(146px,1fr))] gap-4">
		{#each rail.items as item (item.id)}
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
</section>
