<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import panzoom from 'panzoom';
	import html2canvas from 'html2canvas';
	import { saveAs } from 'file-saver';

	export let className = '';
	export let svg = '';

	let instance: any;
	let sceneParentElement: HTMLElement;
	let sceneElement: HTMLElement;

	$: if (sceneElement) {
		instance = panzoom(sceneElement, {
			bounds: true,
			boundsPadding: 0.1,
			zoomSpeed: 0.065
		});
	}

	onDestroy(() => {
		if (instance) {
			instance.dispose();
		}
	});

	async function downloadSVGAsPNG() {
		if (!sceneElement) return;
		try {
			// 暂时禁用 panzoom
			if (instance) {
				instance.dispose();
			}

			// 使用 html2canvas 渲染
			const canvas = await html2canvas(sceneElement, { useCORS: true });
			const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'));
			if (!blob) return;

			const date = new Date();
			const timestamp =
				date.getFullYear() +
				('0' + (date.getMonth() + 1)).slice(-2) +
				('0' + date.getDate()).slice(-2) +
				'_' +
				('0' + date.getHours()).slice(-2) +
				('0' + date.getMinutes()).slice(-2);

			const imageName = `mermaid_${timestamp}.png`;

			saveAs(blob, imageName);
		} catch (error) {
			console.error('图片下载失败:', error);
			alert('图片下载失败，请稍后重试');
		} finally {
			// 重新启用 panzoom
			if (sceneElement) {
				instance = panzoom(sceneElement, {
					bounds: true,
					boundsPadding: 0.1,
					zoomSpeed: 0.065
				});
			}
		}
	}
</script>
