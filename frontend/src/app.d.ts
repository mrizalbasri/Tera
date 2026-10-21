// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			demoMode: boolean;
			user: { username: string; role: 'admin' | 'member' } | null;
			admin: { username: string; role: 'admin' } | null;
		}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
