<script>
	import { io } from 'socket.io-client';
	import { spring } from 'svelte/motion';

	let loadingProgress = spring(0, {
		stiffness: 0.5,
		damping: 1.0
	});

	import { onMount, tick, setContext } from 'svelte';
	import {
		config,
		user,
		theme,
		WEBUI_NAME,
		mobile,
		socket,
		activeUserCount,
		USAGE_POOL
	} from '$lib/stores';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { Toaster, toast } from 'svelte-sonner';

	import { getBackendConfig } from '$lib/apis';
	import { getSessionUser } from '$lib/apis/auths';

	import '../tailwind.css';
	import '../app.css';

	import 'tippy.js/dist/tippy.css';

	import { WEBUI_BASE_URL, WEBUI_HOSTNAME } from '$lib/constants';
	import i18n, { initI18n, getLanguages } from '$lib/i18n';
	import { bestMatchingLanguage } from '$lib/utils';

	setContext('i18n', i18n);

	let loaded = false;
	const BREAKPOINT = 768;

	const setupSocket = () => {
		const _socket = io(`${WEBUI_BASE_URL}` || undefined, {
			reconnection: true,
			reconnectionDelay: 1000,
			reconnectionDelayMax: 5000,
			randomizationFactor: 0.5,
			path: '/ws/socket.io',
			auth: { token: localStorage.token }
		});

		socket.set(_socket);

		_socket.on('connect_error', (err) => {
			console.log('connect_error', err);
		});

		_socket.on('connect', () => {
			console.log('connected', _socket.id);
		});

		_socket.on('reconnect_attempt', (attempt) => {
			console.log('reconnect_attempt', attempt);
		});

		_socket.on('reconnect_failed', () => {
			console.log('reconnect_failed');
		});

		_socket.on('disconnect', (reason, details) => {
			console.log(`Socket ${_socket.id} disconnected due to ${reason}`);
			if (details) {
				console.log('Additional details:', details);
			}
		});

		_socket.on('user-count', (data) => {
			console.log('user-count', data);
			activeUserCount.set(data.count);
		});

		_socket.on('usage', (data) => {
			console.log('usage', data);
			USAGE_POOL.set(data['models']);
		});
	};

	onMount(async () => {
		theme.set(localStorage.theme);

		const updateMobileFlag = () => mobile.set(window.innerWidth < BREAKPOINT);
		updateMobileFlag();
		window.addEventListener('resize', updateMobileFlag);

		const backendConfigPromise = getBackendConfig();
		const languagesPromise = getLanguages();

		initI18n();

		if (!localStorage.locale) {
			const [languages, backendConfig] = await Promise.all([
				languagesPromise,
				backendConfigPromise.catch(() => null)
			]);
			const browserLanguages = navigator.languages || [
				navigator.language || navigator.userLanguage
			];
			const lang =
				backendConfig?.default_locale || bestMatchingLanguage(languages, browserLanguages, 'zh-CN');
			$i18n.changeLanguage(lang);
		}

		let backendConfig = null;
		try {
			backendConfig = await backendConfigPromise;
			console.log('后端配置:', backendConfig);
		} catch (error) {
			console.error('加载后端配置时出错:', error);
			await goto('/error');
			return;
		}

		config.set(backendConfig);
		WEBUI_NAME.set(backendConfig.name);
		// 设置 WebSocket 连接
		setupSocket();

		if (localStorage.token) {
			// 获取会话用户信息
			const sessionUser = await getSessionUser(localStorage.token).catch((error) => {
				toast.error(error);
				return null;
			});

			if (sessionUser) {
				// 将会话用户保存到 store
				user.set(sessionUser);
			} else {
				// 如果会话无效，重定向到 /auth 页面
				localStorage.removeItem('token');
				await goto('/auth');
			}
		} else if ($page.url.pathname !== '/auth') {
			// 如果不在认证页面，重定向到 /auth
			await goto('/auth');
		}

		// 更新进度条
		const progressBar = document.getElementById('progress-bar');
		if (progressBar) {
			loadingProgress.subscribe((value) => {
				requestAnimationFrame(() => {
					if (progressBar) {
						progressBar.style.width = `${Math.min(value, 100)}%`;
					}
				});
			});
			await loadingProgress.set(100);
		}

		// 移除启动画面
		document.getElementById('splash-screen')?.remove();

		// 设置加载完成标志
		loaded = true;

		// 清理函数，移除事件监听器
		return () => {
			window.removeEventListener('resize', updateMobileFlag);
		};
	});
</script>

<svelte:head>
	<title>{$WEBUI_NAME}</title>
	<link crossorigin="anonymous" rel="icon" href="{WEBUI_BASE_URL}/static/favicon.png" />

	<!-- rosepine themes have been disabled as it's not up to date with our latest version. -->
	<!-- feel free to make a PR to fix if anyone wants to see it return -->
	<!-- <link rel="stylesheet" type="text/css" href="/themes/rosepine.css" />
	<link rel="stylesheet" type="text/css" href="/themes/rosepine-dawn.css" /> -->
</svelte:head>

{#if loaded}
	<slot />
{/if}

<Toaster
	theme={$theme.includes('dark')
		? 'dark'
		: $theme === 'system'
			? window.matchMedia('(prefers-color-scheme: dark)').matches
				? 'dark'
				: 'light'
			: 'light'}
	richColors
	position="top-center"
/>
