import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	resolve: {
		alias: {
			'$env/dynamic/private': fileURLToPath(new URL('./src/mocks/env-private.ts', import.meta.url)),
			$lib: fileURLToPath(new URL('./src/lib', import.meta.url)),
			'$env/dynamic/public': fileURLToPath(new URL('./src/mocks/env-public.ts', import.meta.url))
		}
	},
	test: {
		environment: 'node',
		include: ['src/**/*.spec.ts']
	}
});
