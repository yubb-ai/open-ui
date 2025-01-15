<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	export let show = false;
	export let src = '';
	export let alt = '';
	export let isMarkdown: boolean = true;
	export let preview_src_list: any[] = [];

	let previewIndex = preview_src_list.findIndex((item) => item.src === src);
	let mounted = false;
	let previewElement: HTMLElement | null = null;
	let imageElement: HTMLImageElement | null = null;
	let scale = 1;
	let rotation = 0;
	let isDragging = false;
	let startX = 0;
	let startY = 0;
	let offsetX = 0;
	let offsetY = 0;
	let touchStartX = 0;
	let touchStartY = 0;
	let isAnimating = false;
	let animationTimer: any;
	let initialDistance = 0;
	let initialScale = 1;

	const MimeTypes: { [index: string]: string } = {
		jpeg: 'image/jpeg',
		jpg: 'image/jpeg',
		png: 'image/png',
		gif: 'image/gif',
		bmp: 'image/bmp',
		ico: 'image/x-icon',
		tif: 'image/tiff',
		tiff: 'image/tiff',
		webp: 'image/webp',
		svg: 'image/svg+xml',
		avif: 'image/avif',
		heic: 'image/heic',
		heif: 'image/heif',
		jxl: 'image/jxl',
		raw: 'image/x-raw'
	};

	function getMimeType(extension: string) {
		return MimeTypes[extension.toLowerCase()] || 'image/png';
	}

	const closeShow = () => {
		show = false;
	};

	const downloadImage = (url, prefixName = 'image') => {
		const isBase64 = url.startsWith('data:image/');
		let filename = 'image.png';
		let mimeType = 'image/png';

		if (isBase64) {
			const base64Parts = url.split(',');
			const mimeInfo = base64Parts[0].split(';')[0];
			mimeType = mimeInfo.split(':')[1];
			const extension = mimeType.split('/')[1];
			filename = `${prefixName}.${extension}`;

			const base64Data = base64Parts[1];
			const binaryData = atob(base64Data);
			const arrayBuffer = new ArrayBuffer(binaryData.length);
			const uint8Array = new Uint8Array(arrayBuffer);
			for (let i = 0; i < binaryData.length; i++) {
				uint8Array[i] = binaryData.charCodeAt(i);
			}
			const blob = new Blob([uint8Array], { type: mimeType });

			const objectUrl = window.URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = objectUrl;
			link.download = filename;
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			window.URL.revokeObjectURL(objectUrl);
		} else {
			// Handle normal URL download
			const urlParts = url.split('/');
			const fileNameWithExt = urlParts.pop().trim() || '';
			const splitted = fileNameWithExt.split('.');
			const extension = `${(splitted[splitted.length - 1] || 'png').toLowerCase()}`;
			filename = `${(splitted[splitted.length - 2] || 'image').toLowerCase()}.${extension}`;

			fetch(url)
				.then((response) => response.blob())
				.then((blob) => {
					mimeType = getMimeType(extension);
					const newBlob = new Blob([blob], { type: mimeType });
					const objectUrl = window.URL.createObjectURL(newBlob);
					const link = document.createElement('a');
					link.href = objectUrl;
					link.download = filename;
					document.body.appendChild(link);
					link.click();
					document.body.removeChild(link);
					window.URL.revokeObjectURL(objectUrl);
				})
				.catch((error) => console.error('Error downloading image:', error));
		}
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			closeShow();
		} else if (event.key === 'ArrowLeft') {
			previousImage();
		} else if (event.key === 'ArrowRight') {
			nextImage();
		}
	};

	const handleMouseDown = (event: MouseEvent) => {
		isDragging = true;
		startX = event.clientX - offsetX;
		startY = event.clientY - offsetY;
	};

	const handleMouseUp = () => {
		isDragging = false;
	};

	const handleMouseMove = (event: MouseEvent) => {
		if (!isDragging) return;
		offsetX = event.clientX - startX;
		offsetY = event.clientY - startY;
	};

	const handleWheel = (event: WheelEvent) => {
		if (!imageElement) return;
		const zoomSpeed = -event.deltaY * 0.001;
		const newScale = scale + zoomSpeed;
		const rect = imageElement.getBoundingClientRect();
		const mouseX = event.clientX - rect.left;
		const mouseY = event.clientY - rect.top;

		scale = Math.max(0.1, newScale);

		const scaleDelta = scale - newScale;

		offsetX -= mouseX * scaleDelta;
		offsetY -= mouseY * scaleDelta;
	};

	const handleTouchStart = (event: TouchEvent) => {
		if (event.touches.length === 1) {
			touchStartX = event.touches[0].clientX;
		} else if (event.touches.length === 2) {
			initialDistance = getDistance(event.touches[0], event.touches[1]);
			initialScale = scale;
			touchStartX = (event.touches[0].clientX + event.touches[1].clientX) / 2;
			touchStartY = (event.touches[0].clientY + event.touches[1].clientY) / 2;
		}
	};

	const handleTouchMove = (event: TouchEvent) => {
		if (event.touches.length === 2) {
			const currentDistance = getDistance(event.touches[0], event.touches[1]);
			const zoomAmount = (currentDistance - initialDistance) * 0.005;
			const newScale = initialScale + zoomAmount;
			scale = Math.max(0.1, newScale);
			const rect = imageElement!.getBoundingClientRect();
			const touchX = (event.touches[0].clientX + event.touches[1].clientX) / 2 - rect.left;
			const touchY = (event.touches[0].clientY + event.touches[1].clientY) / 2 - rect.top;

			const scaleDelta = scale - newScale;

			offsetX -= touchX * scaleDelta;
			offsetY -= touchY * scaleDelta;
		}
	};

	const handleTouchEnd = (event: TouchEvent) => {
		if (event.changedTouches.length === 1) {
			const touchEndX = event.changedTouches[0].clientX;
			const deltaX = touchEndX - touchStartX;
			if (deltaX > 50) {
				previousImage();
			} else if (deltaX < -50) {
				nextImage();
			}
		}
		initialDistance = 0;
		initialScale = scale;
	};
	const getDistance = (touch1: Touch, touch2: Touch) => {
		const xDiff = touch1.clientX - touch2.clientX;
		const yDiff = touch1.clientY - touch2.clientY;
		return Math.sqrt(xDiff * xDiff + yDiff * yDiff);
	};
	const animateButton = (element: HTMLElement) => {
		if (isAnimating) return;
		isAnimating = true;
		element.classList.add('filter', 'drop-shadow-md', 'brightness-125');
		animationTimer = setTimeout(() => {
			element.classList.remove('filter', 'drop-shadow-md', 'brightness-125');
			isAnimating = false;
		}, 150);
	};

	const resetScale = () => {
		scale = 1;
	};
	const resetRotate = () => {
		rotation = 0;
	};
	const zoomIn = (e: any) => {
		animateButton(e.currentTarget);
		scale += 0.2;
	};

	const zoomOut = (e: any) => {
		animateButton(e.currentTarget);
		scale -= 0.2;
	};

	const rotateLeft = (e: any) => {
		animateButton(e.currentTarget);
		rotation -= 90;
	};

	const rotateRight = (e: any) => {
		animateButton(e.currentTarget);
		rotation += 90;
	};

	const nextImage = () => {
		if (preview_src_list && preview_src_list.length > 0) {
			previewIndex = (previewIndex + 1) % preview_src_list.length;
			src = preview_src_list[previewIndex].src;
			alt = preview_src_list[previewIndex].alt;
			resetScale();
			resetRotate();
			offsetX = 0;
			offsetY = 0;
		}
	};

	const previousImage = () => {
		if (preview_src_list && preview_src_list.length > 0) {
			previewIndex = (previewIndex - 1 + preview_src_list.length) % preview_src_list.length;
			src = preview_src_list[previewIndex].src;
			alt = preview_src_list[previewIndex].alt;
			resetScale();
			resetRotate();
			offsetX = 0;
			offsetY = 0;
		}
	};

	onMount(() => {
		mounted = true;
		if (preview_src_list && preview_src_list.length > 0) {
			src = preview_src_list[previewIndex]?.src;
			alt = preview_src_list[previewIndex]?.alt;
		}
	});

	$: if (show && previewElement) {
		document.body.appendChild(previewElement);
		window.addEventListener('keydown', handleKeyDown);
		document.body.style.overflow = 'hidden';
	} else if (previewElement) {
		window.removeEventListener('keydown', handleKeyDown);
		document.body.removeChild(previewElement);
		document.body.style.overflow = 'unset';
	}

	onDestroy(() => {
		show = false;

		if (previewElement) {
			document.body.removeChild(previewElement);
		}
	});
</script>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={previewElement}
		class="font-primary fixed modal fixed top-0 right-0 left-0 bottom-0 bg-black text-white w-full min-h-screen h-screen flex justify-center z-[9999] overflow-hidden overscroll-contain"
		on:mouseup={handleMouseUp}
		on:wheel={handleWheel}
		on:touchstart={handleTouchStart}
		on:touchmove={handleTouchMove}
		on:touchend={handleTouchEnd}
	>
		<div class="absolute top-0 left-0 w-full flex justify-between p-2 z-[99999] select-none">
			<div class="flex gap-2">
				<button
					class="bg-transparent p-2 border-none bg-opacity-20 rounded-lg p-2 outline-none cursor-pointer text-white transition-all duration-200 ease-in-out hover:opacity-80 hover:scale-110 shadow-md rounded-lg hover:bg-opacity-50"
					on:click={() => {
						closeShow();
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						class="w-6 h-6"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<div class="flex gap-2">
				<button
					class="bg-transparent p-2 border-none bg-opacity-20 rounded-lg p-2 outline-none cursor-pointer text-white transition-all duration-200 ease-in-out hover:bg-opacity-50 rounded-lg"
					on:click={() => {
						if (isMarkdown) {
							window.open(src, '_blank').focus();
						} else {
							downloadImage(src, alt);
						}
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-6 h-6"
					>
						<path
							d="M10.75 2.75a.75.75 0 0 0-1.5 0v8.614L6.295 8.235a.75.75 0 1 0-1.09 1.03l4.25 4.5a.75.75 0 0 0 1.09 0l4.25-4.5a.75.75 0 0 0-1.09-1.03l-2.955 3.129V2.75Z"
						/>
						<path
							d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z"
						/>
					</svg>
				</button>
			</div>
		</div>
		<button
			class="absolute top-1/2 -translate-y-1/2 bg-gray-900 bg-opacity-20 border-none outline-none cursor-pointer text-white transition-colors duration-200 ease-in-out p-2 z-[99999] hover:bg-opacity-50 left-2 rounded-lg"
			on:click={previousImage}
			aria-label="Previous Image"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="1.5"
				stroke="currentColor"
				class="w-6 h-6"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="m15.75 19.5-7.5-7.5 7.5-7.5" />
			</svg>
		</button>
		<div
			class="mx-auto h-full flex justify-center items-center select-none cursor-grab active:cursor-grabbing"
			on:mousedown={handleMouseDown}
		>
			<img
				bind:this={imageElement}
				{src}
				{alt}
				class="object-scale-down select-none max-w-full max-h-full transition-transform duration-200 ease-in-out"
				draggable="false"
				style="transform: translate( {offsetX}px, {offsetY}px) scale({scale}) rotate({rotation}deg);"
			/>
		</div>
		<button
			class="absolute top-1/2 -translate-y-1/2 bg-gray-900 bg-opacity-20 border-none outline-none cursor-pointer text-white transition-colors duration-200 ease-in-out p-2 z-[99999] hover:bg-opacity-50 right-2 rounded-lg"
			on:click={nextImage}
			aria-label="Next Image"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="1.5"
				stroke="currentColor"
				class="w-6 h-6"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
			</svg>
		</button>
		<div
			class="absolute bottom-[25px] left-1/2 -translate-x-1/2 flex gap-2 select-none z-[99999] bg-gray-900 bg-opacity-20 rounded-lg p-1 w-fit"
		>
			<span class="absolute top-[-30px] left-1/2 -translate-x-1/2 text-white text-sm"
				><strong>{previewIndex + 1} / {preview_src_list.length}</strong></span
			>
			<button
				class="bg-transparent p-2 border-none outline-none cursor-pointer text-white transition-colors duration-200 ease-in-out hover:bg-opacity-50 rounded-lg transform-button"
				on:click={zoomIn}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="w-6 h-6"
				>
					<circle cx="11" cy="11" r="8"></circle><line x1="21" x2="16.65" y1="21" y2="16.65"
					></line><line x1="8" x2="14" y1="11" y2="11"></line></svg
				>
			</button>
			<button
				class="bg-transparent p-2 border-none outline-none cursor-pointer text-white transition-colors duration-200 ease-in-out hover:bg-opacity-50 rounded-lg transform-button"
				on:click={zoomOut}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="w-6 h-6"
				>
					<circle cx="11" cy="11" r="8"></circle><line x1="21" x2="16.65" y1="21" y2="16.65"
					></line><line x1="11" x2="11" y1="8" y2="14"></line><line x1="8" x2="14" y1="11" y2="11"
					></line></svg
				>
			</button>
			<button
				class="bg-transparent p-2 border-none outline-none cursor-pointer text-white transition-colors duration-200 ease-in-out hover:bg-opacity-50 rounded-lg transform-button"
				on:click={rotateLeft}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="w-6 h-6"
				>
					<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"
					></path></svg
				>
			</button>
			<button
				class="bg-transparent p-2 border-none outline-none cursor-pointer text-white transition-colors duration-200 ease-in-out hover:bg-opacity-50 rounded-lg transform-button"
				on:click={rotateRight}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="w-6 h-6"
				>
					<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"></path><path d="M21 3v5h-5"
					></path></svg
				>
			</button>
		</div>
	</div>
{/if}
