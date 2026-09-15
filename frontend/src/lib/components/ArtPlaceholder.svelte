<script lang="ts">
	let {
		artKey,
		hasArt = false,
		src,
		size = '68px',
		radius = 'rounded-xs',
		textClass = 'text-2xs font-bold tracking-wider text-muted-2'
	}: {
		artKey: string;
		hasArt?: boolean;
		src?: string;
		size?: string;
		radius?: string;
		textClass?: string;
	} = $props();
</script>

<div
	class="cover relative flex shrink-0 items-center justify-center overflow-hidden {radius}"
	style="width:{size};height:{size}"
>
	{#if hasArt && src}
		<img {src} alt="" class="absolute inset-0 h-full w-full object-cover" />
	{:else}
		<span class={textClass}>{artKey}</span>
	{/if}
</div>

<style>
	.cover {
		background-color: var(--color-border);
		background-image: repeating-linear-gradient(
			135deg,
			var(--color-border-strong) 0 2px,
			transparent 2px 7px
		);
	}
</style>
