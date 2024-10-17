<script>
	import { marked } from 'marked';
	import { replaceTokens, processResponseContent } from '$lib/utils';
	import { user } from '$lib/stores';
	import 'katex/dist/katex.min.css';
	import { throttle } from 'lodash';

	import markedKatexExtension from '$lib/utils/marked/katex-extension';

	import MarkdownTokens from './Markdown/MarkdownTokens.svelte';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let id;
	export let content;
	export let model = null;
	export let save = false;
	export let bufferTime;

	let tokens = [];

	const options = {
		throwOnError: false
	};

	marked.use(markedKatexExtension(options));

	const throttledBufferTime = Number(bufferTime) || 50;

	let previousProcessedContent = '';
	let previousMessageContent = '';
	let processedContent = '';

	const processContentThrottled = throttle(() => {
		if (content) {
			if (Math.abs(content.length - previousProcessedContent.length) > 20) {
				processedContent = replaceTokens(processResponseContent(content), model?.name, $user?.name);
				previousProcessedContent = content;
			} else {
				processedContent += content.slice(previousMessageContent.length);
			}
			previousMessageContent = content;
			tokens = marked.lexer(processedContent);
		}
	}, throttledBufferTime);

	$: (async () => {
		if (content) {
			tokens = marked.lexer(
				replaceTokens(processResponseContent(content), model?.name, $user?.name)
			);
		} else {
			processContentThrottled();
		}
	})();
</script>

{#key id}
	<MarkdownTokens
		{tokens}
		{id}
		{save}
		on:update={(e) => {
			dispatch('update', e.detail);
		}}
		on:code={(e) => {
			dispatch('code', e.detail);
		}}
	/>
{/key}
