<script lang="ts">
	import { getBackendConfig, getWebhookUrl, updateWebhookUrl } from '$lib/apis';
	import { getAdminConfig, updateAdminConfig } from '$lib/apis/auths';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import { config } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let adminConfig = null;
	let webhookUrl = '';

	const updateHandler = async () => {
		webhookUrl = await updateWebhookUrl(localStorage.token, webhookUrl);
		const res = await updateAdminConfig(localStorage.token, adminConfig);

		if (res) {
			saveHandler();
		} else {
			toast.error(i18n.t('Failed to update settings'));
		}
	};

	onMount(async () => {
		await Promise.all([
			(async () => {
				adminConfig = await getAdminConfig(localStorage.token);
			})(),

			(async () => {
				webhookUrl = await getWebhookUrl(localStorage.token);
			})()
		]);
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		{#if adminConfig !== null}
			<div>
				<div class=" mb-3 text-sm font-medium">{$i18n.t('General Settings')}</div>

				<div class="  flex w-full justify-between pr-2">
					<div class=" self-center text-xs font-medium">{$i18n.t('Enable New Sign Ups')}</div>

					<Switch bind:state={adminConfig.ENABLE_SIGNUP} />
				</div>

				{#if adminConfig.ENABLE_SIGNUP}
					<div class="  my-3 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Default User Role')}</div>
						<div class="flex items-center relative">
							<select
								class="dark:bg-gray-900 w-fit pr-8 rounded px-2 text-xs bg-transparent outline-none text-right"
								bind:value={adminConfig.DEFAULT_USER_ROLE}
								placeholder="Select a role"
							>
								<option value="pending">{$i18n.t('pending')}</option>
								<option value="user">{$i18n.t('user')}</option>
								<option value="vip">{$i18n.t('vip')}</option>
								<option value="svip">{$i18n.t('svip')}</option>
								<option value="admin">{$i18n.t('admin')}</option>
							</select>
						</div>
					</div>

					<div class="w-full flex flex-col space-y-4">
						<div class="flex flex-col space-y-2">
							<div class="text-xs font-medium">
								{$i18n.t('Default User Expire Duration')}
							</div>
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:bg-gray-850 dark:text-gray-300 outline-none"
								type="number"
								placeholder="1"
								bind:value={adminConfig.DEFAULT_USER_EXPIRE_DURATION}
								min="1"
							/>
						</div>

						<div class="  my-3 flex w-full justify-between">
							<div class=" self-center text-xs font-medium">
								{$i18n.t('Default User Expire Unit')}
							</div>
							<div class="flex items-center relative">
								<select
									class="dark:bg-gray-900 w-fit pr-8 rounded px-2 text-xs bg-transparent outline-none text-right"
									bind:value={adminConfig.DEFAULT_USER_EXPIRE_UNIT}
									placeholder="Select User Expire Unit"
								>
									<option value="year">{$i18n.t('year')}</option>
									<option value="month">{$i18n.t('month')}</option>
									<option value="week">{$i18n.t('week')}</option>
									<option value="day">{$i18n.t('day')}</option>
								</select>
							</div>
						</div>
					</div>

					<hr class=" dark:border-gray-850 my-2" />

					<div class="my-3 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Enable Turnstile SignUp Check')}
						</div>

						<Switch bind:state={adminConfig.TURNSTILE_SIGNUP_CHECK} />
					</div>

					<div class="my-3 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Enable Turnstile Login Check')}
						</div>

						<Switch bind:state={adminConfig.TURNSTILE_LOGIN_CHECK} />
					</div>

					{#if adminConfig.TURNSTILE_SIGNUP_CHECK || adminConfig.TURNSTILE_LOGIN_CHECK}
						<div class=" w-full justify-between">
							<div class="my-0.5 flex gap-2">
								<input
									class="flex-1 w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
									placeholder={$i18n.t('Turnstile Site Key')}
									bind:value={adminConfig.TURNSTILE_SITE_KEY}
									required
								/>

								<SensitiveInput
									placeholder={$i18n.t('Turnstile Secret Key')}
									bind:value={adminConfig.TURNSTILE_SECRET_KEY}
								/>
							</div>
						</div>
					{/if}

					<div class=" w-full justify-between">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs font-medium">
								{$i18n.t('Supported Registered Email Suffix')}
							</div>
						</div>

						<div class="flex mt-2 space-x-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
								type="text"
								placeholder={''}
								bind:value={adminConfig.REGISTERED_EMAIL_SUFFIX}
							/>
						</div>
						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('Valid Format:')}
							<span class=" text-gray-300 font-medium"
								>{$i18n.t("Multiple mailbox suffixes are separated by ','")}</span
							>
						</div>
					</div>
				{/if}

				<hr class=" dark:border-gray-850 my-2" />

				<div class="my-3 flex w-full items-center justify-between pr-2">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Show Admin Details in Account Pending Overlay')}
					</div>

					<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} />
				</div>

				<div class="my-3 flex w-full items-center justify-between pr-2">
					<div class=" self-center text-xs font-medium">{$i18n.t('Enable Community Sharing')}</div>

					<Switch bind:state={adminConfig.ENABLE_COMMUNITY_SHARING} />
				</div>

				<div class="my-3 flex w-full items-center justify-between pr-2">
					<div class=" self-center text-xs font-medium">{$i18n.t('Enable Message Rating')}</div>

					<Switch bind:state={adminConfig.ENABLE_MESSAGE_RATING} />
				</div>

				<hr class=" dark:border-gray-850 my-2" />

				<div class=" w-full justify-between">
					<div class="flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('JWT Expiration')}</div>
					</div>

					<div class="flex mt-2 space-x-2">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="text"
							placeholder={`e.g.) "30m","1h", "10d". `}
							bind:value={adminConfig.JWT_EXPIRES_IN}
						/>
					</div>

					<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
						{$i18n.t('Valid time units:')}
						<span class=" text-gray-300 font-medium"
							>{$i18n.t("'s', 'm', 'h', 'd', 'w' or '-1' for no expiration.")}</span
						>
					</div>
				</div>

				<hr class=" dark:border-gray-850 my-2" />

				<div class=" w-full justify-between">
					<div class="flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Renewal URL')}</div>
					</div>

					<div class="flex mt-2 space-x-2">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="text"
							placeholder={''}
							bind:value={adminConfig.ADMIN_URL}
						/>
					</div>
				</div>

				<hr class=" dark:border-gray-850 my-2" />

				<div class=" w-full justify-between">
					<div class="flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Webhook URL')}</div>
					</div>

					<div class="flex mt-2 space-x-2">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="text"
							placeholder={`https://example.com/webhook`}
							bind:value={webhookUrl}
						/>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
