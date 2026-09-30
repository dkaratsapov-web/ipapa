(function ($) {
	'use strict';

	const IPAPAWidgets = {
		globalBound: false,

		init() {
			this.initScope(document);
			this.bindGlobalEvents();
		},

		initScope(scope) {
			const $scope = scope && scope.jquery ? scope : $(scope || document);

			if ($scope.hasClass('ipapa-catalog-menu')) {
				this.initCatalogMenu($scope);
			}

			$scope.find('.ipapa-catalog-menu').each((_, element) => {
				this.initCatalogMenu($(element));
			});

			if ($scope.hasClass('ipapa-product-showcase')) {
				this.initProductShowcase($scope);
			}

			$scope.find('.ipapa-product-showcase').each((_, element) => {
				this.initProductShowcase($(element));
			});
		},

		bindGlobalEvents() {
			if (this.globalBound) {
				return;
			}

			this.globalBound = true;

			$(document).on('click', (event) => {
				$('.ipapa-catalog-menu.is-open').each((_, element) => {
					const $menu = $(element);
					if (!$menu.is(event.target) && !$menu.has(event.target).length) {
						this.closeCatalogMenu($menu);
					}
				});
			});

			$(document).on('keydown', (event) => {
				if (event.key !== 'Escape') {
					return;
				}

				$('.ipapa-catalog-menu.is-open').each((_, element) => {
					this.closeCatalogMenu($(element));
				});
			});
		},

		initCatalogMenu($menu) {
			if ($menu.data('ipapaCatalogInit')) {
				return;
			}

			$menu.data('ipapaCatalogInit', true);

			const $toggle = $menu.find('.ipapa-catalog-menu__toggle-button').first();
			const hoverEnabled = String($menu.data('open-mode') || 'hover') === 'hover';
			const updateExpanded = (isOpen) => {
				$toggle.attr('aria-expanded', isOpen ? 'true' : 'false');
			};

			$toggle.on('click', (event) => {
				event.preventDefault();
				event.stopPropagation();

				const isOpen = $menu.hasClass('is-open');
				$('.ipapa-catalog-menu.is-open').not($menu).each((_, element) => {
					this.closeCatalogMenu($(element));
				});

				$menu.toggleClass('is-open', !isOpen);
				updateExpanded(!isOpen);
			});

			$menu.on('mouseenter focusin', () => {
				if (!hoverEnabled) {
					return;
				}

				updateExpanded(true);
			});

			$menu.on('mouseleave', () => {
				if (!hoverEnabled || $menu.hasClass('is-open')) {
					return;
				}

				updateExpanded(false);
			});

			$menu.on('focusout', () => {
				if (!hoverEnabled || $menu.hasClass('is-open')) {
					return;
				}

				window.setTimeout(() => {
					if (!$menu.find(':focus').length) {
						updateExpanded(false);
					}
				}, 0);
			});

			$menu.on('click', '.ipapa-catalog-menu__item', () => {
				if ($menu.data('close-on-item-click') !== 'yes') {
					return;
				}

				if (!$menu.hasClass('is-open')) {
					return;
				}

				this.closeCatalogMenu($menu);
			});
		},

		closeCatalogMenu($menu) {
			$menu.removeClass('is-open');
			$menu.find('.ipapa-catalog-menu__toggle-button').attr('aria-expanded', 'false');
		},

		initProductShowcase($block) {
			if ($block.data('ipapaShowcaseInit')) {
				return;
			}

			$block.data('ipapaShowcaseInit', true);
			this.initGallery($block);
			this.initVariations($block);
			this.bindSimpleButtons($block);
		},

		initGallery($block) {
			$block.on('click', '.ipapa-product-showcase__dot', (event) => {
				event.preventDefault();
				const $dot = $(event.currentTarget);
				const index = parseInt($dot.data('slide'), 10) || 0;
				const $slides = $block.find('.ipapa-product-showcase__slide');
				const $dots = $block.find('.ipapa-product-showcase__dot');

				$slides.removeClass('ipapa-product-showcase__slide--active').attr('aria-hidden', 'true');
				$slides.eq(index).addClass('ipapa-product-showcase__slide--active').attr('aria-hidden', 'false');
				$dots.removeClass('ipapa-product-showcase__dot--active');
				$dot.addClass('ipapa-product-showcase__dot--active');
			});
		},

		initVariations($block) {
			$block.find('form.ipapa-product-showcase__form').each((_, formElement) => {
				const $form = $(formElement);
				if ($form.data('ipapaVariationInit')) {
					return;
				}

				$form.data('ipapaVariationInit', true);

				const $price = $block.find('.ipapa-product-showcase__price').first();
				if ($price.length) {
					$form.data('basePriceHtml', $price.html());
				}

				if (typeof $.fn.wc_variation_form === 'function') {
					$form.wc_variation_form();
				}

				$form.on('click', '.ipapa-product-showcase__option', (event) => {
					event.preventDefault();
					const $option = $(event.currentTarget);
					if ($option.hasClass('is-disabled')) {
						return;
					}

					const attributeName = String($option.data('attribute-name'));
					const value = String($option.data('value'));
					const $select = $form.find(`select[name="${attributeName}"]`);
					if (!$select.length) {
						return;
					}

					$select.val($select.val() === value ? '' : value).trigger('change');
					this.syncVariationOptions($form);
				});

				$form.on('change', '.variations select', () => {
					this.syncVariationOptions($form);
				});

				$form.on('found_variation', (event, variation) => {
					this.syncVariationOptions($form);
					if ($price.length && variation && variation.price_html) {
						$price.html(variation.price_html);
					}
				});

				$form.on('hide_variation reset_data', () => {
					this.syncVariationOptions($form);
					if ($price.length) {
						$price.html($form.data('basePriceHtml') || $price.html());
					}
				});

				$form.on('submit', (event) => {
					if (!window.wc_add_to_cart_params) {
						return;
					}

					event.preventDefault();

					const variationId = parseInt($form.find('input.variation_id').val(), 10);
					if (!variationId) {
						return;
					}

					const payload = $form.serialize();
					const $button = $form.find('.ipapa-product-showcase__button--variable').first();
					this.ajaxAddToCart(payload, $button);
				});

				$form.find('.variations select').trigger('change');
				this.syncVariationOptions($form);
			});
		},

		syncVariationOptions($form) {
			$form.find('.ipapa-product-showcase__option').each((_, element) => {
				const $option = $(element);
				const attributeName = String($option.data('attribute-name'));
				const value = String($option.data('value'));
				const $select = $form.find(`select[name="${attributeName}"]`);
				if (!$select.length) {
					return;
				}

				const selected = String($select.val() || '');
				const $nativeOption = $select.find('option').filter((__, optionElement) => String($(optionElement).val()) === value).first();
				const disabled = !$nativeOption.length || $nativeOption.prop('disabled');

				$option.toggleClass('is-active', selected === value && !disabled);
				$option.toggleClass('is-disabled', !!disabled);
				$option.prop('disabled', !!disabled);
			});

			const $button = $form.find('.ipapa-product-showcase__button--variable');
			const variationReady = parseInt($form.find('input.variation_id').val(), 10) > 0;
			$button.prop('disabled', !variationReady).toggleClass('disabled', !variationReady);
		},

		bindSimpleButtons($block) {
			$block.on('click', '.ipapa-product-showcase__button--simple', (event) => {
				event.preventDefault();
				if (!window.wc_add_to_cart_params) {
					return;
				}

				const $button = $(event.currentTarget);
				const productId = parseInt($button.data('product-id'), 10);
				const quantity = parseInt($button.data('quantity'), 10) || 1;
				if (!productId) {
					return;
				}

				this.ajaxAddToCart(
					{
						product_id: productId,
						quantity,
						'add-to-cart': productId
					},
					$button
				);
			});
		},

		ajaxAddToCart(payload, $button) {
			const params = window.wc_add_to_cart_params;
			if (!params || !params.wc_ajax_url) {
				return;
			}

			const endpoint = params.wc_ajax_url.replace('%%endpoint%%', 'add_to_cart');
			this.setButtonState($button, 'loading');

			$.ajax({
				url: endpoint,
				type: 'POST',
				dataType: 'json',
				data: payload,
				success: (response) => {
					if (response && response.error && response.product_url) {
						window.location = response.product_url;
						return;
					}

					if (response && response.fragments) {
						$.each(response.fragments, (selector, value) => {
							$(selector).replaceWith(value);
						});
					}

					$(document.body).trigger('added_to_cart', [response ? response.fragments : {}, response ? response.cart_hash : '', $button]);
					this.setButtonState($button, 'added');
					window.setTimeout(() => this.setButtonState($button, 'idle'), 1200);
				},
				error: () => {
					this.setButtonState($button, 'idle');
				}
			});
		},

		setButtonState($button, state) {
			if (!$button || !$button.length) {
				return;
			}

			const $text = $button.find('.ipapa-product-showcase__button-text');
			const defaultText = $button.data('default-text') || $text.text();
			const addedText = $button.data('added-text') || defaultText;

			$button.removeClass('is-loading is-added');

			if (state === 'loading') {
				$button.addClass('is-loading').prop('disabled', true);
				return;
			}

			if (state === 'added') {
				$button.addClass('is-added').prop('disabled', true);
				$text.text(addedText);
				return;
			}

			$text.text(defaultText);
			if ($button.hasClass('ipapa-product-showcase__button--variable')) {
				const ready = parseInt($button.closest('form').find('.variation_id').val(), 10) > 0;
				$button.prop('disabled', !ready).toggleClass('disabled', !ready);
			} else {
				$button.prop('disabled', false);
			}
		}
	};

	$(function () {
		IPAPAWidgets.init();
	});

	$(document.body).on('updated_wc_div updated_cart_totals wc_fragments_refreshed', function () {
		IPAPAWidgets.init();
	});

	window.addEventListener('elementor/frontend/init', () => {
		const addHandler = ($scope) => {
			IPAPAWidgets.initScope($scope);
		};

		elementorFrontend.hooks.addAction('frontend/element_ready/ipapa_catalog_menu.default', addHandler);
		elementorFrontend.hooks.addAction('frontend/element_ready/ipapa_product_showcase.default', addHandler);
	});

	window.IPAPAWidgets = IPAPAWidgets;
})(jQuery);
