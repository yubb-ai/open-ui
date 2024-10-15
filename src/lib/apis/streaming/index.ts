import { EventSourceParserStream } from 'eventsource-parser/stream';
import type { ParsedEvent } from 'eventsource-parser';

type TextStreamUpdate = {
	done: boolean;
	value: string;
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	citations?: any;
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	error?: any;
	usage?: ResponseUsage;
};

type ResponseUsage = {
	/** Including images and tools if any */
	prompt_tokens: number;
	/** The tokens generated */
	completion_tokens: number;
	/** Sum of the above two fields */
	total_tokens: number;
};

// createOpenAITextStream takes a responseBody with a SSE response,
// and returns an async generator that emits delta updates with large deltas chunked into random sized chunks
export async function createOpenAITextStream(
	responseBody: ReadableStream<Uint8Array>,
	splitLargeDeltas: boolean
): Promise<AsyncGenerator<TextStreamUpdate>> {
	const eventStream = responseBody
		.pipeThrough(new TextDecoderStream())
		.pipeThrough(new EventSourceParserStream())
		.getReader();
	let iterator = openAIStreamToIterator(eventStream);
	if (splitLargeDeltas) {
		iterator = streamLargeDeltasAsRandomChunks(iterator);
	}
	return iterator;
}

async function* openAIStreamToIterator(
	reader: ReadableStreamDefaultReader<ParsedEvent>
): AsyncGenerator<TextStreamUpdate> {
	// 初始延迟设为20ms，设定最小延迟和最大延迟上下限
	let delay = 20;
	// 最小延迟，避免过快
	const minDelay = 10;
	// 最大延迟，避免过慢
	const maxDelay = 30;
	// 平滑因子，用于动态调整速率
	const smoothingFactor = 0.1;

	function adjustDelay(newTime: number) {
		// 指数移动平均平滑处理时间，并控制在合理范围内
		delay = delay * (1 - smoothingFactor) + newTime * smoothingFactor;
		delay = Math.max(minDelay, Math.min(maxDelay, delay));
	}

	// 记录上一次循环的结束时间
	let lastLoopTime = Date.now();

	while (true) {
		const loopStartTime = Date.now();
		const { value, done } = await reader.read();
		if (done) {
			yield { done: true, value: '' };
			break;
		}
		if (!value) {
			continue;
		}
		const data = value.data;
		if (data.startsWith('[DONE]')) {
			yield { done: true, value: '' };
			break;
		}

		try {
			const parsedData = JSON.parse(data);
			console.log(parsedData);

			if (parsedData.error) {
				yield { done: true, value: '', error: parsedData.error };
				break;
			}

			if (parsedData.citations) {
				yield { done: false, value: '', citations: parsedData.citations };
				continue;
			}

			yield {
				done: false,
				value: parsedData.choices?.[0]?.delta?.content ?? '',
				usage: parsedData.usage
			};

			// 计算处理时间
			const processingTime = Date.now() - loopStartTime;

			// 动态调整延迟
			adjustDelay(processingTime);

			// 计算应等待的时间，使总循环时间接近目标延迟
			const elapsedTime = Date.now() - lastLoopTime;
			let sleepTime = delay - elapsedTime;
			sleepTime = Math.max(0, sleepTime);

			// 更新上一次循环的结束时间
			lastLoopTime = Date.now();

			// 等待计算出的时间
			if (sleepTime > 0) {
				await sleep(sleepTime);
			}
		} catch (e) {
			console.error('Error extracting delta from SSE event:', e);
		}
	}
}

// streamLargeDeltasAsRandomChunks will chunk large deltas (length > 5) into random sized chunks between 1-3 characters
// This is to simulate a more fluid streaming, even though some providers may send large chunks of text at once
async function* streamLargeDeltasAsRandomChunks(
	iterator: AsyncGenerator<TextStreamUpdate>
): AsyncGenerator<TextStreamUpdate> {
	for await (const textStreamUpdate of iterator) {
		if (textStreamUpdate.done) {
			yield textStreamUpdate;
			return;
		}
		if (textStreamUpdate.citations) {
			yield textStreamUpdate;
			continue;
		}
		let content = textStreamUpdate.value;
		if (content.length < 5) {
			yield { done: false, value: content };
			continue;
		}
		while (content != '') {
			const chunkSize = Math.min(Math.floor(Math.random() * 3) + 1, content.length);
			const chunk = content.slice(0, chunkSize);
			yield { done: false, value: chunk };
			// Do not sleep if the tab is hidden
			// Timers are throttled to 1s in hidden tabs
			if (document?.visibilityState !== 'hidden') {
				await sleep(10);
			}
			content = content.slice(chunkSize);
		}
	}
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
