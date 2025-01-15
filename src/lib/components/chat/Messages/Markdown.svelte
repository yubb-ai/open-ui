<script>
	import { marked } from 'marked';
	import { replaceTokens, processResponseContent } from '$lib/utils';
	import { user } from '$lib/stores';
	import { throttle } from 'lodash';

	import markedKatexExtension from '$lib/utils/marked/katex-extension';

	import MarkdownTokens from './Markdown/MarkdownTokens.svelte';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let id;
	export let content;
	export let model = null;
	export let save = false;
	export let bufferTime = 30;

	let tokens = [];

	const options = {
		throwOnError: false
	};

	marked.use(markedKatexExtension(options));

	const throttledBufferTime = Number(bufferTime) || 30;

	const processContentThrottled = throttle(() => {
		tokens = marked.lexer(replaceTokens(processResponseContent(content), model?.name, $user?.name));
	}, throttledBufferTime);

	$: (async () => {
		if (content) {
			processContentThrottled();
		} else {
			// 当消息为空或者消息收到Done返回"" 的时候，直接显示
			tokens = marked.lexer(
				replaceTokens(processResponseContent(content), model?.name, $user?.name)
			);
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
