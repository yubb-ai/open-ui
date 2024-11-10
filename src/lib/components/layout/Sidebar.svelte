<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import {
		user,
		chats,
		settings,
		showSettings,
		chatId,
		tags,
		showSidebar,
		mobile,
		showArchivedChats,
		pinnedChats,
		scrollPaginationEnabled,
		currentChatPage,
		temporaryChatEnabled,
		showArtifacts
	} from '$lib/stores';
	import { onMount, getContext, tick } from 'svelte';

	const i18n = getContext('i18n');

	import { updateUserSettings } from '$lib/apis/users';
	import {
		deleteChatById,
		getChatList,
		getChatById,
		getChatListByTagName,
		updateChatById,
		getAllChatTags,
		archiveChatById,
		cloneChatById
	} from '$lib/apis/chats';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import ArchivedChatsModal from './Sidebar/ArchivedChatsModal.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import ChatItem from './Sidebar/ChatItem.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';

	const BREAKPOINT = 768;

	let navElement;
	let search = '';

	let shiftKey = false;

	let selectedChatId = null;
	let deleteChat = null;

	let showDeleteConfirm = false;
	let showDropdown = false;

	let selectedTagName = null;

	let filteredChatList = [];

	// Pagination variables
	let chatListLoading = false;
	let allChatsLoaded = false;

	$: filteredChatList = $chats.filter((chat) => {
		if (search === '') {
			return true;
		} else {
			let title = chat.title.toLowerCase();
			const query = search.toLowerCase();

			let contentMatches = false;
			// Access the messages within chat.chat.messages
			if (chat.chat && chat.chat.messages && Array.isArray(chat.chat.messages)) {
				contentMatches = chat.chat.messages.some((message) => {
					// Check if message.content exists and includes the search query
					return message.content && message.content.toLowerCase().includes(query);
				});
			}

			return title.includes(query) || contentMatches;
		}
	});

	const enablePagination = async () => {
		// Reset pagination variables
		currentChatPage.set(1);
		allChatsLoaded = false;
		await chats.set(await getChatList(localStorage.token, $currentChatPage));

		// Enable pagination
		scrollPaginationEnabled.set(true);
	};

	const loadMoreChats = async () => {
		chatListLoading = true;

		currentChatPage.set($currentChatPage + 1);
		const newChatList = await getChatList(localStorage.token, $currentChatPage);

		// once the bottom of the list has been reached (no results) there is no need to continue querying
		allChatsLoaded = newChatList.length === 0;
		await chats.set([...$chats, ...newChatList]);

		chatListLoading = false;
	};

	onMount(async () => {
		mobile.subscribe((e) => {
			if ($showSidebar && e) {
				showSidebar.set(false);
			}

			if (!$showSidebar && !e) {
				showSidebar.set(true);
			}
		});

		showSidebar.set(!$mobile ? localStorage.sidebar === 'true' : false);
		showSidebar.subscribe((value) => {
			localStorage.sidebar = value;
		});

		await pinnedChats.set(await getChatListByTagName(localStorage.token, 'pinned'));
		await enablePagination();

		let touchstart;
		let touchend;

		function checkDirection() {
			const screenWidth = window.innerWidth;
			const swipeDistance = Math.abs(touchend.screenX - touchstart.screenX);
			if (touchstart.clientX < 40 && swipeDistance >= screenWidth / 8) {
				if (touchend.screenX < touchstart.screenX) {
					showSidebar.set(false);
				}
				if (touchend.screenX > touchstart.screenX) {
					showSidebar.set(true);
				}
			}
		}

		const onTouchStart = (e) => {
			touchstart = e.changedTouches[0];
			console.log(touchstart.clientX);
		};

		const onTouchEnd = (e) => {
			touchend = e.changedTouches[0];
			checkDirection();
		};

		const onKeyDown = (e) => {
			if (e.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (e) => {
			if (e.key === 'Shift') {
				shiftKey = false;
			}
		};

		const onFocus = () => {};

		const onBlur = () => {
			shiftKey = false;
			selectedChatId = null;
		};

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);

		window.addEventListener('touchstart', onTouchStart);
		window.addEventListener('touchend', onTouchEnd);

		window.addEventListener('focus', onFocus);
		window.addEventListener('blur', onBlur);

		return () => {
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);

			window.removeEventListener('touchstart', onTouchStart);
			window.removeEventListener('touchend', onTouchEnd);

			window.removeEventListener('focus', onFocus);
			window.removeEventListener('blur', onBlur);
		};
	});

	// Helper function to fetch and add chat content to each chat
	const enrichChatsWithContent = async (chatList) => {
		const enrichedChats = await Promise.all(
			chatList.map(async (chat) => {
				const chatDetails = await getChatById(localStorage.token, chat.id).catch((error) => null); // Handle error or non-existent chat gracefully
				if (chatDetails) {
					chat.chat = chatDetails.chat; // Assuming chatDetails.chat contains the chat content
				}
				return chat;
			})
		);

		await chats.set(enrichedChats);
	};

	const saveSettings = async (updated) => {
		await settings.set({ ...$settings, ...updated });
		await updateUserSettings(localStorage.token, { ui: $settings });
		location.href = '/';
	};

	const deleteChatHandler = async (id) => {
		const res = await deleteChatById(localStorage.token, id).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			if ($chatId === id) {
				await chatId.set('');
				await tick();
				goto('/');
			}

			allChatsLoaded = false;
			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));

			await pinnedChats.set(await getChatListByTagName(localStorage.token, 'pinned'));
		}
	};
</script>

<ArchivedChatsModal
	bind:show={$showArchivedChats}
	on:change={async () => {
		await chats.set(await getChatList(localStorage.token));
	}}
/>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete chat?')}
	on:confirm={() => {
		deleteChatHandler(deleteChat.id);
	}}
>
	<div class=" text-sm text-gray-500 flex-1 line-clamp-3">
		{$i18n.t('This will delete')} <span class="  font-semibold">{deleteChat.title}</span>.
	</div>
</DeleteConfirmDialog>

<!-- svelte-ignore a11y-no-static-element-interactions -->

{#if $showSidebar}
	<div
		class=" fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-black/60 w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain"
		on:mousedown={() => {
			showSidebar.set(!$showSidebar);
		}}
	/>
{/if}

<div
	bind:this={navElement}
	id="sidebar"
	class="h-screen max-h-[100dvh] min-h-screen select-none {$showSidebar
		? 'md:relative w-[260px]'
		: '-translate-x-[260px] w-[0px]'} bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-200 text-sm transition fixed z-50 top-0 left-0
        "
	data-state={$showSidebar}
>
	<div
		class="py-2.5 my-auto flex flex-col justify-between h-screen max-h-[100dvh] w-[260px] z-50 {$showSidebar
			? ''
			: 'invisible'}"
	>
		<div class="px-2.5 flex justify-between space-x-1 text-gray-600 dark:text-gray-400">
			<a
				id="sidebar-new-chat-button"
				class="flex flex-1 justify-between rounded-xl px-2 h-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
				href="/"
				draggable="false"
				on:click={async () => {
					selectedChatId = null;
					await goto('/');
					const newChatButton = document.getElementById('new-chat-button');
					setTimeout(() => {
						newChatButton?.click();
						if ($mobile) {
							showSidebar.set(false);
						}
					}, 0);
				}}
			>
				<div class="self-center mx-1.5">
					<img
						crossorigin="anonymous"
						src="{WEBUI_BASE_URL}/static/favicon.png"
						class=" size-6 -translate-x-1.5 rounded-full"
						alt="logo"
					/>
				</div>
				<div class=" self-center font-medium text-sm text-gray-850 dark:text-white font-primary">
					{$i18n.t('New Chat')}
				</div>
				<div class="self-center ml-auto">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						stroke-width="0.1"
						viewBox="0 0 24 24"
						stroke="currentColor"
						class="size-5"
					>
						<path
							d="M15.6729 3.91287C16.8918 2.69392 18.8682 2.69392 20.0871 3.91287C21.3061 5.13182 21.3061 7.10813 20.0871 8.32708L14.1499 14.2643C13.3849 15.0293 12.3925 15.5255 11.3215 15.6785L9.14142 15.9899C8.82983 16.0344 8.51546 15.9297 8.29289 15.7071C8.07033 15.4845 7.96554 15.1701 8.01005 14.8586L8.32149 12.6785C8.47449 11.6075 8.97072 10.615 9.7357 9.85006L15.6729 3.91287ZM18.6729 5.32708C18.235 4.88918 17.525 4.88918 17.0871 5.32708L11.1499 11.2643C10.6909 11.7233 10.3932 12.3187 10.3014 12.9613L10.1785 13.8215L11.0386 13.6986C11.6812 13.6068 12.2767 13.3091 12.7357 12.8501L18.6729 6.91287C19.1108 6.47497 19.1108 5.76499 18.6729 5.32708ZM11 3.99929C11.0004 4.55157 10.5531 4.99963 10.0008 5.00007C9.00227 5.00084 8.29769 5.00827 7.74651 5.06064C7.20685 5.11191 6.88488 5.20117 6.63803 5.32695C6.07354 5.61457 5.6146 6.07351 5.32698 6.63799C5.19279 6.90135 5.10062 7.24904 5.05118 7.8542C5.00078 8.47105 5 9.26336 5 10.4V13.6C5 14.7366 5.00078 15.5289 5.05118 16.1457C5.10062 16.7509 5.19279 17.0986 5.32698 17.3619C5.6146 17.9264 6.07354 18.3854 6.63803 18.673C6.90138 18.8072 7.24907 18.8993 7.85424 18.9488C8.47108 18.9992 9.26339 19 10.4 19H13.6C14.7366 19 15.5289 18.9992 16.1458 18.9488C16.7509 18.8993 17.0986 18.8072 17.362 18.673C17.9265 18.3854 18.3854 17.9264 18.673 17.3619C18.7988 17.1151 18.8881 16.7931 18.9393 16.2535C18.9917 15.7023 18.9991 14.9977 18.9999 13.9992C19.0003 13.4469 19.4484 12.9995 20.0007 13C20.553 13.0004 21.0003 13.4485 20.9999 14.0007C20.9991 14.9789 20.9932 15.7808 20.9304 16.4426C20.8664 17.116 20.7385 17.7136 20.455 18.2699C19.9757 19.2107 19.2108 19.9756 18.27 20.455C17.6777 20.7568 17.0375 20.8826 16.3086 20.9421C15.6008 21 14.7266 21 13.6428 21H10.3572C9.27339 21 8.39925 21 7.69138 20.9421C6.96253 20.8826 6.32234 20.7568 5.73005 20.455C4.78924 19.9756 4.02433 19.2107 3.54497 18.2699C3.24318 17.6776 3.11737 17.0374 3.05782 16.3086C2.99998 15.6007 2.99999 14.7266 3 13.6428V10.3572C2.99999 9.27337 2.99998 8.39922 3.05782 7.69134C3.11737 6.96249 3.24318 6.3223 3.54497 5.73001C4.02433 4.7892 4.78924 4.0243 5.73005 3.54493C6.28633 3.26149 6.88399 3.13358 7.55735 3.06961C8.21919 3.00673 9.02103 3.00083 9.99922 3.00007C10.5515 2.99964 10.9996 3.447 11 3.99929Z"
							fill="currentColor"
						>
						</path>
					</svg>
				</div>
			</a>

			<button
				class=" cursor-pointer px-2 py-2 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-900 transition"
				on:click={() => {
					showSidebar.set(!$showSidebar);
				}}
			>
				<div class=" m-auto self-center">
					<MenuLines />
				</div>
			</button>
		</div>

		{#if $user?.role === 'admin'}
			<div class="px-2.5 flex justify-center text-gray-800 dark:text-gray-200">
				<a
					class="flex-grow flex space-x-3 rounded-xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
					href="/workspace"
					on:click={() => {
						selectedChatId = null;
						chatId.set('');

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
					draggable="false"
				>
					<div class="self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="size-[1.1rem]"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 0 0 2.25-2.25V6a2.25 2.25 0 0 0-2.25-2.25H6A2.25 2.25 0 0 0 3.75 6v2.25A2.25 2.25 0 0 0 6 10.5Zm0 9.75h2.25A2.25 2.25 0 0 0 10.5 18v-2.25a2.25 2.25 0 0 0-2.25-2.25H6a2.25 2.25 0 0 0-2.25 2.25V18A2.25 2.25 0 0 0 6 20.25Zm9.75-9.75H18a2.25 2.25 0 0 0 2.25-2.25V6A2.25 2.25 0 0 0 18 3.75h-2.25A2.25 2.25 0 0 0 13.5 6v2.25a2.25 2.25 0 0 0 2.25 2.25Z"
							/>
						</svg>
					</div>

					<div class="flex self-center">
						<div class=" self-center font-medium text-sm font-primary">{$i18n.t('Workspace')}</div>
					</div>
				</a>
			</div>
		{/if}

		<div
			class="relative flex flex-col flex-1 overflow-y-auto {$temporaryChatEnabled
				? 'opacity-20'
				: ''}"
		>
			{#if $temporaryChatEnabled}
				<div class="absolute z-40 w-full h-full flex justify-center"></div>
			{/if}

			<div class="px-2 mt-0.5 mb-2 flex justify-center space-x-2">
				<div class="flex w-full rounded-xl" id="chat-search">
					<div class="self-center pl-3 py-2 rounded-l-xl bg-transparent">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>

					<input
						class="w-full rounded-r-xl py-1.5 pl-2.5 pr-4 text-sm bg-transparent dark:text-gray-300 outline-none"
						placeholder={$i18n.t('Search')}
						bind:value={search}
						on:focus={async () => {
							// TODO: migrate backend for more scalable search mechanism
							scrollPaginationEnabled.set(false);
							await chats.set(await getChatList(localStorage.token)); // when searching, load all chats
							enrichChatsWithContent($chats);
						}}
					/>
				</div>
			</div>

			{#if $tags.filter((t) => t.name !== 'pinned').length > 0}
				<div class="px-3.5 mb-1 flex gap-0.5 flex-wrap">
					<button
						class="px-2.5 py-[1px] text-xs transition {selectedTagName === null
							? 'bg-gray-100 dark:bg-gray-900'
							: ' '} rounded-md font-medium"
						on:click={async () => {
							selectedTagName = null;
							await enablePagination();
						}}
					>
						{$i18n.t('all')}
					</button>
					{#each $tags.filter((t) => t.name !== 'pinned') as tag}
						<button
							class="px-2.5 py-[1px] text-xs transition {selectedTagName === tag.name
								? 'bg-gray-100 dark:bg-gray-900'
								: ''}  rounded-md font-medium"
							on:click={async () => {
								selectedTagName = tag.name;
								scrollPaginationEnabled.set(false);
								let chatIds = await getChatListByTagName(localStorage.token, tag.name);
								if (chatIds.length === 0) {
									await tags.set(await getAllChatTags(localStorage.token));

									// if the tag we deleted is no longer a valid tag, return to main chat list view
									await enablePagination();
								}
								await chats.set(chatIds);

								chatListLoading = false;
							}}
						>
							{tag.name}
						</button>
					{/each}
				</div>
			{/if}

			{#if !search && $pinnedChats.length > 0}
				<div class="pl-2 py-2 flex flex-col space-y-1">
					<div class="">
						<div class="w-full pl-2.5 text-xs text-gray-500 dark:text-gray-500 font-medium pb-1.5">
							{$i18n.t('Pinned')}
						</div>

						{#each $pinnedChats as chat, idx}
							<ChatItem
								{chat}
								{shiftKey}
								selected={selectedChatId === chat.id}
								on:select={() => {
									selectedChatId = chat.id;
								}}
								on:unselect={() => {
									selectedChatId = null;
								}}
								on:delete={(e) => {
									if ((e?.detail ?? '') === 'shift') {
										deleteChatHandler(chat.id);
									} else {
										deleteChat = chat;
										showDeleteConfirm = true;
									}
								}}
							/>
						{/each}
					</div>
				</div>
			{/if}

			<div class="pl-2 my-2 flex-1 flex flex-col space-y-1 overflow-y-auto scrollbar-hidden">
				{#each filteredChatList as chat, idx}
					{#if idx === 0 || (idx > 0 && chat.time_range !== filteredChatList[idx - 1].time_range)}
						<div
							class="w-full pl-2.5 text-xs text-gray-500 dark:text-gray-500 font-medium {idx === 0
								? ''
								: 'pt-5'} pb-0.5"
						>
							{$i18n.t(chat.time_range)}
							<!-- localisation keys for time_range to be recognized from the i18next parser (so they don't get automatically removed):
							{$i18n.t('Today')}
							{$i18n.t('Yesterday')}
							{$i18n.t('Previous 7 days')}
							{$i18n.t('Previous 30 days')}
							{$i18n.t('January')}
							{$i18n.t('February')}
							{$i18n.t('March')}
							{$i18n.t('April')}
							{$i18n.t('May')}
							{$i18n.t('June')}
							{$i18n.t('July')}
							{$i18n.t('August')}
							{$i18n.t('September')}
							{$i18n.t('October')}
							{$i18n.t('November')}
							{$i18n.t('December')}
							-->
						</div>
					{/if}

					<ChatItem
						{chat}
						{shiftKey}
						selected={selectedChatId === chat.id}
						on:select={() => {
							selectedChatId = chat.id;
						}}
						on:unselect={() => {
							selectedChatId = null;
						}}
						on:delete={(e) => {
							if ((e?.detail ?? '') === 'shift') {
								deleteChatHandler(chat.id);
							} else {
								deleteChat = chat;
								showDeleteConfirm = true;
							}
						}}
					/>
				{/each}

				{#if $scrollPaginationEnabled && !allChatsLoaded}
					<Loader
						on:visible={(e) => {
							if (!chatListLoading) {
								loadMoreChats();
							}
						}}
					>
						<div class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2">
							<Spinner className=" size-4" />
							<div class=" ">Loading...</div>
						</div>
					</Loader>
				{/if}
			</div>
		</div>

		<div class="px-2.5">
			<!-- <hr class=" border-gray-900 mb-1 w-full" /> -->

			<div class="flex flex-col font-primary">
				{#if $user !== undefined}
					<UserMenu
						role={$user.role}
						on:show={(e) => {
							if (e.detail === 'archived-chat') {
								showArchivedChats.set(true);
							}
						}}
					>
						<button
							class=" flex rounded-xl py-3 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							on:click={() => {
								showDropdown = !showDropdown;
							}}
						>
							<div class=" self-center mr-3">
								<img
									src={$user.profile_image_url}
									class=" max-w-[30px] object-cover rounded-full"
									alt="User profile"
								/>
							</div>
							<div class=" self-center font-medium">{$user.name}</div>
						</button>
					</UserMenu>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	.scrollbar-hidden:active::-webkit-scrollbar-thumb,
	.scrollbar-hidden:focus::-webkit-scrollbar-thumb,
	.scrollbar-hidden:hover::-webkit-scrollbar-thumb {
		visibility: visible;
	}
	.scrollbar-hidden::-webkit-scrollbar-thumb {
		visibility: hidden;
	}
</style>
