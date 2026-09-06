/**
 * Post-process orval output to fix a known issue: orval emits
 * `export type X = typeof X[keyof typeof X];` *before* `export const X = {...}`,
 * AND `export const Y = {...X, ...Z,}` before `export const X = {...}`,
 * both of which TypeScript rejects under strict mode.
 *
 * Strategy:
 *   1. Collect every `export const NAME = {...} as const;` declaration.
 *   2. Build a dependency graph: const Y depends on const X if Y's body
 *      contains `{...X,` or `{...X }` (spread).
 *   3. Topologically sort so that each const appears AFTER its dependencies.
 *   4. Strip them all from the file, then re-emit in sorted order.
 *
 * Type aliases (`export type X = typeof X[...]`) reference the const, so
 * we emit the type aliases at the very end of the file. The orval-emitted
 * type aliases reference the consts via `typeof X` which works once X is
 * declared (anywhere in the module).
 */
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const GEN_DIR = 'src/lib/api/generated';

for (const file of readdirSync(GEN_DIR).filter((f) => f.endsWith('.ts'))) {
	const path = join(GEN_DIR, file);
	const src = readFileSync(path, 'utf8');

	// Match each `export const NAME = {...} as const;` block.
	// Non-greedy on the body to pick the matching closing brace.
	// Trailing `;` is optional — orval sometimes omits it when the next
	// line is another `export const` in the same logical block.
	const constRe = /export const (\w+) = \{[\s\S]*?\} as const;?/g;
	const collected = [];
	let m;
	while ((m = constRe.exec(src)) !== null) {
		collected.push({ name: m[1], body: m[0], index: m.index });
	}

	if (collected.length === 0) continue;

	// Build dependency graph: const Y depends on X if Y's body
	// contains a spread reference `{...X,` or `{...X }` to another const.
	const allNames = new Set(collected.map((c) => c.name));
	const deps = new Map();
	for (const c of collected) {
		const myDeps = new Set();
		const spreadRe = /\.\.\.(\w+)\b/g;
		let sm;
		while ((sm = spreadRe.exec(c.body)) !== null) {
			if (allNames.has(sm[1]) && sm[1] !== c.name) {
				myDeps.add(sm[1]);
			}
		}
		deps.set(c.name, myDeps);
	}

	// Topological sort (Kahn's algorithm).
	const inDegree = new Map();
	for (const c of collected) {
		inDegree.set(c.name, deps.get(c.name).size);
	}
	const dependents = new Map();
	for (const c of collected) {
		for (const d of deps.get(c.name)) {
			if (!dependents.has(d)) dependents.set(d, new Set());
			dependents.get(d).add(c.name);
		}
	}
	const queue = collected.filter((c) => inDegree.get(c.name) === 0).map((c) => c.name);
	const sorted = [];
	while (queue.length > 0) {
		const name = queue.shift();
		sorted.push(name);
		for (const dependent of dependents.get(name) ?? []) {
			inDegree.set(dependent, inDegree.get(dependent) - 1);
			if (inDegree.get(dependent) === 0) queue.push(dependent);
		}
	}

	// If we couldn't sort all (cycle), fall back to original order.
	if (sorted.length !== collected.length) {
		console.warn(`[fix-orval-order] cycle detected in ${file}, falling back to original order`);
		continue;
	}

	// Strip all const decls from the source.
	let stripped = src;
	for (const { body, index } of collected.slice().reverse()) {
		stripped = stripped.slice(0, index) + stripped.slice(index + body.length);
	}
	// Clean up multiple blank lines that result from stripping.
	stripped = stripped.replace(/\n{3,}/g, '\n\n');

	// Re-emit in sorted order at the top of the file.
	const blocksByName = new Map(collected.map((c) => [c.name, c.body]));
	const reordered = sorted.map((n) => blocksByName.get(n)).join('\n\n');
	const out = reordered + '\n\n' + stripped.trimStart();

	writeFileSync(path, out);
	console.log(`[fix-orval-order] reordered ${collected.length} const decls in ${file} (topo-sorted)`);
}