(() => {
    const sync = (form) => {
        const selection = {
            color: form.querySelector('input[name="preorder_color"]:checked')?.value || '',
            storage: form.querySelector('input[name="preorder_storage"]:checked')?.value || '',
        };
        form.querySelectorAll('[data-preorder-config]').forEach((select) => {
            Array.from(select.options).forEach((option) => {
                const conditions = JSON.parse(option.dataset.when || '{}');
                const allowed = Object.entries(conditions).every(([key, values]) => values.includes(selection[key]));
                option.disabled = !allowed;
                option.hidden = !allowed;
            });
            if (!select.selectedOptions.length || select.selectedOptions[0].disabled) {
                const first = Array.from(select.options).find((option) => !option.disabled);
                select.value = first?.value || '';
            }
            selection[select.dataset.preorderConfig] = select.value;
        });
    };
    const init = (root) => root.querySelectorAll('form').forEach(sync);
    document.addEventListener('change', (event) => {
        const form = event.target.closest('form');
        if (form) sync(form);
    });
    // Colour can also be selected with the product gallery arrows.
    document.addEventListener('click', (event) => {
        const form = event.target.closest('form');
        if (form) sync(form);
    });
    init(document);
    new MutationObserver((records) => {
        records.forEach((record) => record.addedNodes.forEach((node) => {
            if (!(node instanceof Element)) return;
            if (node.matches('form')) sync(node);
            init(node);
        }));
    }).observe(document.body, {childList: true, subtree: true});
})();
