export type Tone = 'ink' | 'amber' | 'cyan' | 'red';

export interface Fact {
	label: string;
	value: string | number;
	tone: Tone;
}

export interface RailItem {
	id: number;
	href: string;
	name: string;
	meta: string;
	score: number;
	art_key: string;
	has_art: boolean;
	art_type: 'release' | 'artist' | 'label';
}

export interface Rail {
	title: string;
	note: string;
	items: RailItem[];
}

export interface MissingRelease {
	name: string;
	year: string | null;
	href: string;
}

export interface Link {
	name: string;
	href?: string;
}

export interface ContextRow {
	label: string;
	value: string;
}

export interface DiaryEntry {
	id: number;
	date: string;
	text: string;
}

export interface DetailView {
	kind: 'release' | 'artist' | 'label';
	id: number;
	eyebrow: string;
	name: string;
	art_key: string;
	has_art: boolean;
	crumb_label: string;
	crumb_href: string;
	links: Link[];
	subline: string;
	tags: string[];
	facts: Fact[];
	is_release: boolean;
	edit_href: string;
	show_delete: boolean;
	source_href: string | null;
	rails: Rail[];
	// release-only
	relisten_href?: string;
	delete_id?: number;
	delete_type?: string;
	diary_meta?: string;
	entries?: DiaryEntry[];
	context?: ContextRow[];
}

export interface ReleaseEditData {
	id: number;
	name: string;
	year: number | null;
	main_genre: string | null;
	genres: string[];
	rating: number;
	image: string | null;
	listen_date: string | null;
	country: string | null;
	artist: string | null;
	label: string | null;
	collab_artists: string[];
	countries: string[];
}

export interface EntityEditData {
	id: number;
	name: string;
	begin: string | null;
	end: string | null;
	country: string | null;
	image: string | null;
	countries: string[];
}

export interface HomeEntry {
	id: number;
	title: string;
	year: number | null;
	artist: { id: number; name: string } | null;
	label: { id: number; name: string } | null;
	main_genre: string | null;
	subgenres: string[];
	note: string | null;
	rating: number;
	score: number;
	runtime: string;
	track_count: number;
	art_key: string;
	has_art: boolean;
}

export interface HomeEntryGroup {
	label: string;
	meta: string;
	items: HomeEntry[];
}

export interface HomeEntriesResponse {
	groups: HomeEntryGroup[];
	has_next: boolean;
	page: number;
}

export interface HomeGoal {
	type: string;
	amount: number;
	current: number;
	target: number;
	start: string;
	end: string;
	end_year: number;
	on_track: boolean;
	[key: string]: unknown;
}

export interface OnRepeatArtist {
	id: number;
	name: string;
	count: number;
	average_rating: number;
	art_key: string;
	has_art: boolean;
}

export interface HomeData {
	this_year: {
		count: number;
		new_artists: number;
		new_labels: number;
		listening_time: number;
		average_score: number;
		pace: number;
	};
	goal: HomeGoal | null;
	score_spread: { pct: number; is_peak: boolean }[];
	median_score: number;
	on_repeat: OnRepeatArtist[];
	total_logged: number;
	day_of_year: number;
	current_year: number;
}

export interface NewListenData {
	all_genres: string[];
	goal_nudge: string | null;
	today: string;
	total_logged: number;
}

export interface SearchResultItem {
	release: { name: string; mbid: string | null };
	artist: { mbid: string | null; name: string };
	label: { mbid: string | null; name: string };
	date: string | null;
	format: string | null;
	track_count: number | null;
	country: string | null;
	release_group_id: string | null;
	logged: boolean;
	initials: string;
}

export interface BrowseMeta {
	counts: { releases: number; artists: number; labels: number };
	filters: {
		countries: [string, string][];
		genres?: string[];
		types?: string[];
	};
}

export interface BrowseItem {
	id: number;
	href: string;
	name: string;
	meta: string;
	score: number;
	art_key: string;
	has_art: boolean;
	art_type: 'release' | 'artist' | 'label';
}

export interface BrowseResults {
	items: BrowseItem[];
	total: number;
	page: number;
	total_pages: number;
}

export interface StatsKpi {
	label: string;
	value: string;
	sub: string;
}

export interface StatsPeriod {
	chart_note: string;
	kpis: StatsKpi[];
	series: { value: number; label: string; h: number; is_peak: boolean }[];
	rhythm: { label: string; value: string }[];
	histogram: { h: number; is_peak: boolean }[];
	mean: string;
	median: string;
	high_share: string;
	low_share: string;
}

export interface StatsData {
	periods: { key: string; label: string }[];
	active_period: string;
	stats: StatsPeriod;
	genres: { name: string; value: string; w: number }[];
	since: string | null;
}

export interface LeaderboardRow {
	rank: number;
	name: string;
	value: string;
	w: number;
}

export interface LeaderboardBoard {
	title: string;
	note: string;
	rows: LeaderboardRow[];
}

export interface LeaderboardsResponse {
	boards: LeaderboardBoard[];
}

export interface GoalMetric {
	label: string;
	value: string | number;
	sub: string;
	tone: Tone;
}

export interface ActiveGoal {
	status: 'BEHIND PACE' | 'ON TRACK';
	on_track: boolean;
	window: string;
	actual: number;
	target: number;
	type_label: string;
	percent: number;
	progress_w: number;
	pace_w: number;
	progress_label: string;
	pace_label: string;
	metrics: GoalMetric[];
	projection: string;
}

export interface PastGoal {
	title: string;
	window: string;
	w: number;
	result: string;
	badge: 'COMPLETE' | 'MISSED' | string;
	tone: Tone;
}

export interface GoalPreset {
	label: string;
	amount: number;
	end: string;
}

export interface GoalType {
	value: string;
	label: string;
}

export interface GoalsData {
	active_goal: ActiveGoal | null;
	past_goals: PastGoal[];
	current_pace: number;
	today: string;
	default_amount: number;
	default_end: string;
	goal_presets: GoalPreset[];
	goal_types: GoalType[];
}

export interface CompletedGoal {
	type: string;
	amount: number;
	end_year: number;
}

export interface SubmitResponse {
	ok: true;
	completed_goals: CompletedGoal[];
}
