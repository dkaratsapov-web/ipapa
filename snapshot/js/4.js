document.addEventListener('DOMContentLoaded', () => {
	const root = document.querySelector('.ipapa-tradein-page');
	const pricing = window.ipapaTradeInCalculator || {};
	const rawDevices = Array.isArray(pricing.devices) ? pricing.devices : [];
	const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

	if (!root) {
		return;
	}

	const devices = rawDevices
		.map((device) => {
			const models = Array.isArray(device?.models)
				? device.models
						.map((model) => {
							const maxPrice = Array.isArray(model?.variants)
								? model.variants.reduce((result, variant) => {
										const variantPrices = variant?.prices && typeof variant.prices === 'object'
											? Object.values(variant.prices).map((price) => parseNumber(price))
											: [];

										return Math.max(result, ...variantPrices, 0);
								  }, 0)
								: 0;

							return {
								id: String(model?.id || ''),
								name: cleanText(model?.name),
								label: cleanText(model?.shortLabel || model?.name),
								maxPrice,
							};
						})
						.filter((model) => model.id && model.label)
				: [];

			return {
				slug: String(device?.slug || ''),
				label: cleanText(device?.label),
				models,
			};
		})
		.filter((device) => device.slug && device.label && device.models.length);

	const tabs = Array.from(root.querySelectorAll('.ipapa-ti-tab'));
	const modelsContainer = root.querySelector('[data-ti-models]');
	const priceDisplay = root.querySelector('[data-ti-price]');
	const resultCard = root.querySelector('[data-ti-result-card]');

	if (!devices.length || !tabs.length || !modelsContainer || !priceDisplay || !resultCard) {
		return;
	}

	const summary = {
		device: root.querySelector('[data-ti-summary="device"]'),
		model: root.querySelector('[data-ti-summary="model"]'),
		price: root.querySelector('[data-ti-summary="price"]'),
	};

	const initialTab = tabs.find((tab) => tab.classList.contains('ipapa-ti-tab--active')) || tabs[0];
	const state = {
		deviceSlug: initialTab?.dataset.device || devices[0]?.slug || '',
		modelId: modelsContainer.querySelector('[data-ti-option-id].ipapa-ti-option--on')?.dataset.tiOptionId || '',
	};

	let pulseTimeout = 0;

	function parseNumber(value) {
		if (typeof value === 'number' && Number.isFinite(value)) {
			return value;
		}

		const normalized = String(value || '').replace(/[^\d-]/g, '');
		return normalized ? parseInt(normalized, 10) : 0;
	}

	function cleanText(value) {
		return String(value || '').replace(/\s+/g, ' ').trim();
	}

	function formatPrice(value) {
		return `до ${new Intl.NumberFormat('ru-RU').format(Math.max(0, parseNumber(value)))} ₽`;
	}

	function createEmptyState(message) {
		const emptyState = document.createElement('p');
		emptyState.className = 'ipapa-ti-empty-state';
		emptyState.textContent = message;
		return emptyState;
	}

	function setOptionState(option, isActive) {
		if (!option) {
			return;
		}

		option.classList.toggle('ipapa-ti-option--on', isActive);
		option.setAttribute('aria-pressed', String(isActive));

		const box = option.querySelector('.ipapa-ti-box');
		if (box) {
			box.classList.toggle('ipapa-ti-box--checked', isActive);
		}
	}

	function createOptionButton({ active, label, name, price, dataValue }) {
		const button = document.createElement('button');
		const box = document.createElement('span');
		const content = document.createElement('span');
		const title = document.createElement('span');
		const meta = document.createElement('span');

		button.type = 'button';
		button.className = active ? 'ipapa-ti-option ipapa-ti-option--on' : 'ipapa-ti-option';
		button.setAttribute('aria-pressed', active ? 'true' : 'false');
		button.setAttribute('data-ti-option-id', dataValue);
		button.dataset.name = name;
		button.dataset.price = String(price);

		box.className = active ? 'ipapa-ti-box ipapa-ti-box--checked' : 'ipapa-ti-box';
		content.className = 'ipapa-ti-option__content';
		title.className = 'ipapa-ti-option__label';
		title.textContent = label;
		meta.className = 'ipapa-ti-option__meta';
		meta.textContent = formatPrice(price);

		content.append(title, meta);
		button.append(box, content);

		return button;
	}

	function findDevice(deviceSlug) {
		return devices.find((device) => device.slug === deviceSlug) || devices[0] || null;
	}

	function ensureModelState(device) {
		const models = Array.isArray(device?.models) ? device.models : [];

		if (!models.length) {
			state.modelId = '';
			return null;
		}

		if (!models.some((model) => model.id === state.modelId)) {
			state.modelId = models[0].id;
		}

		return models.find((model) => model.id === state.modelId) || models[0] || null;
	}

	function renderTabs() {
		tabs.forEach((tab) => {
			const isActive = tab.dataset.device === state.deviceSlug;
			tab.classList.toggle('ipapa-ti-tab--active', isActive);
			tab.setAttribute('aria-pressed', String(isActive));
		});
	}

	function renderModels() {
		const device = findDevice(state.deviceSlug);
		const model = ensureModelState(device);
		const models = Array.isArray(device?.models) ? device.models : [];

		if (!models.length) {
			modelsContainer.replaceChildren(createEmptyState('Для этой категории цену подскажет менеджер после заявки.'));
			return;
		}

		const buttons = models.map((item) =>
			createOptionButton({
				active: item.id === model?.id,
				label: item.label,
				name: item.name,
				price: item.maxPrice,
				dataValue: item.id,
			})
		);

		modelsContainer.replaceChildren(...buttons);
	}

	function calculateState() {
		const device = findDevice(state.deviceSlug);
		const model = ensureModelState(device);

		return {
			device: cleanText(device?.label) || 'Не выбрано',
			model: cleanText(model?.name) || 'Не выбрано',
			price: parseNumber(model?.maxPrice),
			priceLabel: formatPrice(model?.maxPrice),
		};
	}

	function pulseResultCard() {
		if (reduceMotion) {
			return;
		}

		resultCard.classList.remove('is-pulse');
		window.clearTimeout(pulseTimeout);
		void resultCard.offsetWidth;
		resultCard.classList.add('is-pulse');
		pulseTimeout = window.setTimeout(() => {
			resultCard.classList.remove('is-pulse');
		}, 450);
	}

	function syncSummary(calculatedState) {
		if (summary.device) {
			summary.device.textContent = calculatedState.device;
		}

		if (summary.model) {
			summary.model.textContent = calculatedState.model;
		}

		if (summary.price) {
			summary.price.textContent = calculatedState.priceLabel;
		}
	}

	function refreshEstimate({ pulse = false, scrollToCard = false } = {}) {
		const calculatedState = calculateState();
		priceDisplay.textContent = calculatedState.priceLabel;
		syncSummary(calculatedState);

		if (pulse) {
			pulseResultCard();
		}

		if (scrollToCard && window.innerWidth < 1025) {
			resultCard.scrollIntoView({
				behavior: reduceMotion ? 'auto' : 'smooth',
				block: 'start',
			});
		}

		return calculatedState;
	}

	tabs.forEach((tab) => {
		tab.addEventListener('click', () => {
			const nextDeviceSlug = tab.dataset.device || '';

			if (!nextDeviceSlug || nextDeviceSlug === state.deviceSlug) {
				return;
			}

			state.deviceSlug = nextDeviceSlug;
			state.modelId = '';
			renderTabs();
			renderModels();
			refreshEstimate({ pulse: true });
		});
	});

	modelsContainer.addEventListener('click', (event) => {
		const option = event.target.closest('[data-ti-option-id]');
		if (!option) {
			return;
		}

		const nextModelId = option.dataset.tiOptionId || '';
		if (!nextModelId || nextModelId === state.modelId) {
			return;
		}

		state.modelId = nextModelId;
		renderModels();
		refreshEstimate({ pulse: true, scrollToCard: true });
	});

	renderTabs();
	renderModels();
	refreshEstimate();

	const leadForm = document.querySelector('[data-contacts-lead-form]');
	if (leadForm) {
		leadForm.addEventListener('submit', () => {
			const contextInput = document.getElementById('ipapa-ti-context-message');
			if (!contextInput) {
				return;
			}

			const calculatedState = calculateState();
			contextInput.value = [
				`Устройство: ${calculatedState.device}`,
				`Модель: ${calculatedState.model}`,
				`Предварительная оценка: ${calculatedState.priceLabel}`,
			].join('\n');
		});
	}
});
