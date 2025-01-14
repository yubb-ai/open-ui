<script lang="ts">
	import { getContext } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { marked } from 'marked';

	const i18n = getContext('i18n');

	const helpText = {
		vision: $i18n.t('Model accepts image inputs'),
		usage: $i18n.t(
			'Sends `stream_options: { include_usage: true }` in the request.\nSupported providers will return token usage information in the response when set.'
		),
		base64: $i18n.t('Accepts base64 encoded File objects'),
		createPPT: $i18n.t('在请求中发送 `stream_options: { include_ppt: true }`'),
		createImage: $i18n.t('在请求中发送 `stream_options: { include_image: true }`'),
		createVideo: $i18n.t('在请求中发送 `stream_options: { include_video: true }`'),
		createSearch: $i18n.t('在请求中发送 `stream_options: { include_search: true }`')
	};

	export let capabilities: {
		vision?: boolean;
		usage?: boolean;
		base64?: boolean;
		createPPT?: boolean;
		createImage?: boolean;
		createVideo?: boolean;
		createSearch?: boolean;
	} = {};
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class=" self-center text-sm font-semibold">{$i18n.t('Capabilities')}</div>
	</div>
	<div class="flex flex-col">
		{#each Object.keys(capabilities) as capability}
			<div class=" flex items-center gap-2">
				<Checkbox
					state={capabilities[capability] ? 'checked' : 'unchecked'}
					on:change={(e) => {
						capabilities[capability] = e.detail === 'checked';
					}}
				/>

				<div class=" py-0.5 text-sm capitalize">
					<Tooltip content={marked.parse(helpText[capability])}>
						{$i18n.t(capability)}
					</Tooltip>
				</div>
			</div>
		{/each}
	</div>
</div>
