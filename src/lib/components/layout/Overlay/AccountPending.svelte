<script lang="ts">
	import { getAdminDetails } from '$lib/apis/auths';
	import { onMount, getContext } from 'svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import dayjs from 'dayjs';

	const i18n = getContext('i18n');
	import { user } from '$lib/stores';

	let adminDetails = null;

	onMount(async () => {
		adminDetails = await getAdminDetails(localStorage.token).catch((err) => {
			console.error(err);
			return null;
		});
	});
</script>

<div class="fixed w-full h-full flex z-[999]">
	<div
		class="absolute w-full h-full backdrop-blur-lg bg-white/10 dark:bg-gray-900/50 flex justify-center"
	>
		<div class="m-auto pb-10 flex flex-col justify-center">
			<div class="max-w-md">
				<div class="flex justify-center mb-6">
					<img src="{WEBUI_BASE_URL}/static/favicon.png" class=" w-8 rounded-full" alt="logo" />
				</div>

				<!-- 标题 -->
				<h2 class="text-2xl font-semibold text-center text-gray-800 dark:text-gray-100 mb-4">
					{$i18n.t('Account Activation Pending')}
				</h2>
				<h3 class="text-md text-center text-gray-600 dark:text-gray-300 mb-6">
					{$i18n.t('Contact Admin for WebUI Access')}
				</h3>

				<!-- 状态信息 -->
				<div class="text-center text-sm text-gray-700 dark:text-gray-200 mb-6 mx-4">
					{#if $user && ($user.role === 'pending' || ($user?.expire_at !== null && Number($user?.expire_at) < dayjs().unix()))}
						{$i18n.t(
							'您的账号已过期，账户内容将在七天之内删除，请您尽快点击下面按钮或联系客服续费吧！'
						)}<br />
					{:else if $user && $user.role === 'pending'}
						{$i18n.t('Your account status is currently pending activation.')}<br />
						{$i18n.t(
							'To access the WebUI, please reach out to the administrator. Admins can manage user statuses from the Admin Panel.'
						)}
					{/if}
				</div>

				<div class="mt-4 text-sm font-medium text-center text-gray-700 dark:text-gray-200">
					{#if adminDetails}
						<div>
							{$i18n.t('Admin')}: {adminDetails?.name} ({adminDetails?.email})
						</div>
					{/if}
					<div class="mt-6 mx-auto relative group w-fit">
						<button
							class="relative z-20 flex px-5 py-2 rounded-full bg-blue-500 hover:bg-blue-600 text-white transition font-medium text-sm"
							on:click={async () => {
								location.href = adminDetails?.url;
							}}
						>
							{$i18n.t('点击购买续费')}
						</button>

						<button
							class="text-xs text-center w-full mt-2 text-gray-400 underline"
							on:click={async () => {
								localStorage.removeItem('token');
								location.href = '/auth';
							}}>{$i18n.t('Sign Out')}</button
						>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	/* 移除浏览器默认的数字输入框旋转按钮 */
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		-webkit-appearance: none;
		margin: 0;
	}

	input[type='number'] {
		-moz-appearance: textfield;
	}

	/* 优化日期选择器在移动设备上的显示 */
	@media (max-width: 600px) {
		input[type='datetime-local'] {
			font-size: 16px;
			padding: 10px;
		}
	}
</style>
