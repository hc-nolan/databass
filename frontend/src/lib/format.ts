const RATING_WORDS = [
	'',
	'actively bad',
	"didn't work",
	'flat',
	'thin',
	'fine',
	'solid',
	'really good',
	'excellent',
	'near-perfect',
	'all-timer'
];

export function ratingWord(r: number): string {
	return RATING_WORDS[r] ?? '';
}

export function ratingHint(r: number): string {
	return `${ratingWord(r)} · stored as ${r * 10}%`;
}

export function toneTextClass(tone: string): string {
	switch (tone) {
		case 'amber':
			return 'text-amber';
		case 'cyan':
			return 'text-cyan';
		case 'red':
			return 'text-danger-text';
		default:
			return 'text-ink';
	}
}

export function imageSrc(itemType: string, id: number): string {
	return `/img/${itemType}/${id}`;
}

export function daysBetween(from: string, to: string): number {
	const a = new Date(`${from}T00:00:00Z`).getTime();
	const b = new Date(`${to}T00:00:00Z`).getTime();
	return Math.round((b - a) / 86400000);
}

/**
 * Artist/label begin & end dates come back as Flask's default HTTP-date
 * serialization (e.g. "Mon, 01 Jan 0001 00:00:00 GMT"), and unknown dates
 * are stored as year-1/year-9999 sentinels rather than null. Normalize both
 * into the "" | "YYYY-MM-DD" shape <input type="date"> expects.
 */
export function toDateInputValue(value: string | null): string {
	if (!value) return '';
	const d = new Date(value);
	if (Number.isNaN(d.getTime()) || d.getUTCFullYear() <= 1 || d.getUTCFullYear() >= 9999) return '';
	return d.toISOString().slice(0, 10);
}
