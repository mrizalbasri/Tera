/** Referensi klaim singkat yang mudah dibaca dari UUID, mis. CLM-3F2A. */
export function shortClaimRef(claimId: string): string {
	const clean = claimId.replace(/-/g, '');
	return `CLM-${clean.slice(0, 4).toUpperCase()}`;
}
