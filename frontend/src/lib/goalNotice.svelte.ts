import type { CompletedGoal } from './types';

export const goalNoticeState: { pending: CompletedGoal[] } = $state({ pending: [] });
